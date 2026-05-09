#!/usr/bin/env python3
# coding=utf-8
"""
insdaily topic radar

Fetches public editorial sources, scores article candidates against the
insdaily topic library, and writes a daily topic-selection report.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import textwrap
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET

import feedparser
import requests
import yaml

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


@dataclass
class SourceItem:
    id: str
    title: str
    url: str
    source_id: str
    source_name: str
    source_type: str
    published_at: str = ""
    summary: str = ""
    category: str = ""
    raw_score: float = 0.0
    topic_id: str = ""
    topic_label: str = ""
    angle: str = ""
    accounts: List[str] = field(default_factory=list)
    matched_keywords: List[str] = field(default_factory=list)
    score_notes: List[str] = field(default_factory=list)


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def configured_now(timezone_name: str) -> datetime:
    if ZoneInfo is None:
        return datetime.now(timezone.utc)
    return datetime.now(ZoneInfo(timezone_name))


def parse_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    value = value.strip()
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        pass
    try:
        from email.utils import parsedate_to_datetime

        return parsedate_to_datetime(value)
    except Exception:
        return None


def normalize_text(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_title_key(title: str) -> str:
    title = normalize_text(title).lower()
    title = re.sub(r"[\W_]+", "", title, flags=re.UNICODE)
    return title[:120]


def item_id(source_id: str, title: str, url: str) -> str:
    digest = hashlib.sha1(f"{source_id}|{normalize_title_key(title)}|{url}".encode("utf-8")).hexdigest()
    return digest[:16]


def derive_title_from_url(url: str) -> str:
    path = unquote(urlparse(url).path)
    slug = path.rstrip("/").split("/")[-1]
    slug = re.sub(r"^\d+[-_]", "", slug)
    slug = slug.replace("-", " ").replace("_", " ")
    return normalize_text(slug)


def category_from_url(url: str) -> str:
    path = unquote(urlparse(url).path)
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 1:
        return parts[0]
    return ""


def request_text(url: str, timeout: int = 20) -> str:
    resp = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/xml, text/html, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    resp.raise_for_status()
    content_type = resp.headers.get("content-type", "").lower()
    if "charset=" not in content_type:
        return resp.content.decode("utf-8", errors="replace")
    return resp.text


def collect_rss(source: Dict[str, Any]) -> List[SourceItem]:
    content = request_text(source["url"])
    parsed = feedparser.parse(content)
    items: List[SourceItem] = []
    max_items = int(source.get("max_items") or 0)

    for entry in parsed.entries[: max_items or None]:
        title = normalize_text(entry.get("title", ""))
        if not title:
            continue
        url = entry.get("link", "")
        published = entry.get("published") or entry.get("updated") or ""
        summary = normalize_text(entry.get("summary", ""))
        category = ""
        tags = entry.get("tags") or []
        if tags:
            category = ", ".join(t.get("term", "") for t in tags if t.get("term"))
        items.append(
            SourceItem(
                id=item_id(source["id"], title, url),
                title=title,
                url=url,
                source_id=source["id"],
                source_name=source["name"],
                source_type="rss",
                published_at=published,
                summary=summary[:350],
                category=category,
            )
        )
    return items


def _find_text(node: ET.Element, names: Iterable[str]) -> str:
    for elem in node.iter():
        tag = elem.tag.split("}", 1)[-1]
        if tag in names and elem.text:
            return normalize_text(elem.text)
    return ""


def collect_sitemap(source: Dict[str, Any]) -> List[SourceItem]:
    content = request_text(source["url"])
    root = ET.fromstring(content)
    max_items = int(source.get("max_items") or 0)
    include_categories = set(source.get("include_categories") or [])

    # Support sitemap indexes, but keep this conservative. Some sites expose the
    # index while blocking child sitemaps, so failed children are skipped.
    if root.tag.endswith("sitemapindex"):
        child_urls = []
        for sitemap in root:
            loc = _find_text(sitemap, ["loc"])
            if loc:
                child_urls.append(loc)
        items: List[SourceItem] = []
        follow = int(source.get("follow_sitemaps") or 2)
        for child_url in child_urls[:follow]:
            child = dict(source)
            child["url"] = child_url
            try:
                items.extend(collect_sitemap(child))
            except Exception as exc:
                print(f"[WARN] {source['name']} child sitemap failed: {child_url} ({exc})")
        return items[: max_items or None]

    items = []
    for url_node in root:
        loc = _find_text(url_node, ["loc"])
        if not loc:
            continue
        title = _find_text(url_node, ["title"]) or derive_title_from_url(loc)
        published = _find_text(url_node, ["publication_date", "lastmod"])
        category = category_from_url(loc)

        if include_categories and category and category not in include_categories:
            continue

        items.append(
            SourceItem(
                id=item_id(source["id"], title, loc),
                title=title,
                url=loc,
                source_id=source["id"],
                source_name=source["name"],
                source_type="sitemap",
                published_at=published,
                category=category,
            )
        )
        if max_items and len(items) >= max_items:
            break
    return items


def collect_sources(config: Dict[str, Any]) -> Tuple[List[SourceItem], List[str]]:
    all_items: List[SourceItem] = []
    warnings: List[str] = []
    seen: set[str] = set()
    seen_urls: set[str] = set()

    for source in config.get("sources", []):
        if not source.get("enabled", True):
            if source.get("warn_when_disabled", False):
                note = source.get("note", "disabled")
                warnings.append(f"{source.get('name', source.get('id'))}: skipped ({note})")
            continue
        try:
            if source.get("type") == "rss":
                items = collect_rss(source)
            elif source.get("type") == "sitemap":
                items = collect_sitemap(source)
            else:
                warnings.append(f"{source.get('name', source.get('id'))}: unsupported type {source.get('type')}")
                continue
            for item in items:
                key = normalize_title_key(item.title) or item.url
                if key in seen or (item.url and item.url in seen_urls):
                    continue
                seen.add(key)
                if item.url:
                    seen_urls.add(item.url)
                all_items.append(item)
            print(f"[OK] {source['name']}: {len(items)} items")
        except Exception as exc:
            warning = f"{source.get('name', source.get('id'))}: failed ({type(exc).__name__}: {exc})"
            warnings.append(warning)
            print(f"[WARN] {warning}")

    return all_items, warnings


def keyword_hits(title: str, keywords: List[str]) -> List[str]:
    haystack = title.lower()
    hits = []
    for keyword in keywords:
        if not keyword:
            continue
        needle = str(keyword).lower()
        if needle in haystack:
            hits.append(str(keyword))
    return hits


def recency_score(published_at: str, now: datetime, freshness_days: int) -> Tuple[float, str]:
    dt = parse_datetime(published_at)
    if dt is None:
        return 1.0, "无发布时间"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=now.tzinfo)
    age_hours = max(0.0, (now - dt.astimezone(now.tzinfo)).total_seconds() / 3600)
    if age_hours <= 6:
        return 8.0, "6小时内"
    if age_hours <= 24:
        return 6.0, "24小时内"
    if age_hours <= freshness_days * 24:
        return 3.0, f"{freshness_days}天内"
    return -4.0, f"超过{freshness_days}天"


def score_items(items: List[SourceItem], config: Dict[str, Any]) -> List[SourceItem]:
    source_weights = {s["id"]: float(s.get("weight", 1.0)) for s in config.get("sources", [])}
    topic_groups = config.get("topic_groups", [])
    exclude_signals = config.get("title_signals", {}).get("exclude", [])
    strong_signals = config.get("title_signals", {}).get("strong", [])
    weak_penalties = config.get("title_signals", {}).get("weak_penalty", [])
    app = config.get("app", {})
    now = configured_now(app.get("timezone", "Asia/Shanghai"))
    freshness_days = int(app.get("freshness_days", 3))

    scored: List[SourceItem] = []
    for item in items:
        title = item.title
        if keyword_hits(title, exclude_signals):
            continue
        best: Optional[Dict[str, Any]] = None
        best_hits: List[str] = []
        for group in topic_groups:
            hits = keyword_hits(title, group.get("keywords", []))
            if item.category:
                hits.extend(keyword_hits(item.category, group.get("keywords", [])))
            if not hits:
                continue
            priority = int(group.get("priority", 9))
            group_score = max(2.0, 18.0 - priority * 1.8) + min(12.0, len(set(hits)) * 3.0)
            if best is None or group_score > best["group_score"]:
                best = {**group, "group_score": group_score}
                best_hits = sorted(set(hits), key=hits.index)

        if best is None:
            continue

        score = source_weights.get(item.source_id, 1.0) * 10.0 + float(best["group_score"])
        notes = [f"匹配：{', '.join(best_hits[:5])}"]

        rec_score, rec_note = recency_score(item.published_at, now, freshness_days)
        score += rec_score
        notes.append(rec_note)

        strong_hits = keyword_hits(title, strong_signals)
        if strong_hits:
            score += min(10.0, 2.5 * len(strong_hits))
            notes.append(f"强信号：{', '.join(strong_hits[:3])}")

        penalty_hits = keyword_hits(title, weak_penalties)
        if penalty_hits and best.get("id") != "consumer_lifestyle":
            score -= min(8.0, 2.0 * len(penalty_hits))
            notes.append(f"弱选题扣分：{', '.join(penalty_hits[:3])}")

        clean_len = len(title)
        if 12 <= clean_len <= 90:
            score += 2.0
        elif clean_len > 130:
            score -= 3.0

        item.raw_score = round(score, 1)
        item.topic_id = best.get("id", "")
        item.topic_label = best.get("label", "")
        item.angle = best.get("angle", "")
        item.accounts = list(best.get("accounts", []))
        item.matched_keywords = best_hits
        item.score_notes = notes
        scored.append(item)

    scored.sort(key=lambda x: x.raw_score, reverse=True)
    return scored


def format_time(value: str) -> str:
    dt = parse_datetime(value)
    if not dt:
        return value or "未知时间"
    return dt.strftime("%Y-%m-%d %H:%M")


def title_ideas(item: SourceItem) -> List[str]:
    base = re.sub(r"\s+", " ", item.title).strip(" -")
    if item.topic_id == "celebrity_fashion":
        return [f"{base}，为什么突然被全网盯上？", f"这场造型/人设争议，真正吵的不是美丑"]
    if item.topic_id == "women_relationships":
        return [f"{base}：她们真正害怕的是什么", f"这件事戳中了多少人的关系困境"]
    if item.topic_id == "uk_life_study":
        return [f"{base}，对留学生和海外华人意味着什么？", f"英国这件事，中文圈不能只看热闹"]
    if item.topic_id == "consumer_lifestyle":
        return [f"{base}背后，年轻人的消费正在变", f"一个生活方式变化，正在被海外媒体放大"]
    if item.topic_id == "people_story":
        return [f"{base}：一个人的命运转折，为什么值得写", f"从被看见到被争议，她/他经历了什么"]
    return [f"{base}，为什么中文读者会有感觉？", f"海外这件事，放到中文语境里更有意思"]


def select_diverse(scored: List[SourceItem], top_n: int, max_per_topic: int) -> List[SourceItem]:
    if max_per_topic <= 0:
        return scored[:top_n]

    picked: List[SourceItem] = []
    topic_counts: Dict[str, int] = {}
    deferred: List[SourceItem] = []

    for item in scored:
        topic = item.topic_id or "unknown"
        if topic_counts.get(topic, 0) < max_per_topic:
            picked.append(item)
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        else:
            deferred.append(item)
        if len(picked) >= top_n:
            return picked

    for item in deferred:
        picked.append(item)
        if len(picked) >= top_n:
            break
    return picked


def build_report(
    scored: List[SourceItem],
    all_count: int,
    warnings: List[str],
    config: Dict[str, Any],
    generated_at: datetime,
) -> str:
    app = config.get("app", {})
    top_n = int(app.get("top_n", 18))
    max_per_topic = int(app.get("max_per_topic", 0))
    top_items = select_diverse(scored, top_n, max_per_topic)

    by_topic: Dict[str, int] = {}
    for item in scored:
        by_topic[item.topic_label] = by_topic.get(item.topic_label, 0) + 1

    lines = [
        "# insdaily 选题雷达",
        "",
        f"- 生成时间：{generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 抓取素材：{all_count} 条；命中选题库：{len(scored)} 条；输出 Top {len(top_items)}",
        f"- 覆盖方向：{', '.join(f'{k} {v}' for k, v in sorted(by_topic.items(), key=lambda x: x[1], reverse=True)[:8]) or '暂无'}",
        "",
    ]

    if warnings:
        lines.append("## 源状态提醒")
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

    lines.append("## 今日优先选题")
    if not top_items:
        lines.append("")
        lines.append("本轮没有明显命中选题库的素材。可以放宽关键词、增加 RSS 源，或手动查看 People/公众号参考源。")
    for idx, item in enumerate(top_items, 1):
        lines.extend(
            [
                "",
                f"### {idx}. [{item.topic_label}] {item.title}",
                f"- 来源：{item.source_name}；时间：{format_time(item.published_at)}；分数：{item.raw_score}",
                f"- 链接：{item.url}",
                f"- 推荐角度：{item.angle}",
                f"- 对标参考：{', '.join(item.accounts) if item.accounts else '无'}",
                f"- 判断依据：{'; '.join(item.score_notes)}",
                "- 备选标题：",
            ]
        )
        for idea in title_ideas(item):
            lines.append(f"  - {idea}")

    lines.extend(["", "## 今天可以选的打法"])
    for option in config.get("strategy_options", []):
        lines.append(f"- {option['name']}：{option['use_when']} 建议产出：{option['output']}")

    lines.extend(
        [
            "",
            "## 使用建议",
            "- 外网源用于找事实和新鲜度，公众号参考源用于判断中文语境里的角度、标题和情绪。",
            "- TMZ/BuzzFeed 类素材适合快反，但涉及人物关系、法律、健康和争议时要用 Guardian/NYT/HK01 或官方声明二次确认。",
            "- People 当前在本网络下返回 402，建议人工浏览或后续接入代理/第三方 RSS 后再自动化。",
        ]
    )

    return "\n".join(lines).strip() + "\n"


def save_outputs(scored: List[SourceItem], report: str, config: Dict[str, Any], generated_at: datetime) -> Tuple[Path, Path]:
    output_root = Path(config.get("app", {}).get("output_dir", "output/insdaily"))
    day_dir = output_root / generated_at.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    stem = generated_at.strftime("%H-%M")
    md_path = day_dir / f"{stem}-topic-report.md"
    json_path = day_dir / f"{stem}-topic-report.json"

    md_path.write_text(report, encoding="utf-8")
    json_path.write_text(
        json.dumps([asdict(item) for item in scored], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return md_path, json_path


def send_feishu_text(webhook_url: str, content: str) -> None:
    max_len = 28000
    chunks = textwrap.wrap(content, width=max_len, replace_whitespace=False, drop_whitespace=False)
    for chunk in chunks or [content[:max_len]]:
        resp = requests.post(
            webhook_url,
            json={"msg_type": "text", "content": {"text": chunk}},
            timeout=20,
        )
        resp.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run insdaily topic radar")
    parser.add_argument("--config", default="config/insdaily_sources.yaml", help="Path to insdaily source config")
    parser.add_argument("--push", action="store_true", help="Push report to Feishu when FEISHU_WEBHOOK_URL is set")
    args = parser.parse_args()

    config = load_yaml(Path(args.config))
    generated_at = configured_now(config.get("app", {}).get("timezone", "Asia/Shanghai"))

    items, warnings = collect_sources(config)
    scored = score_items(items, config)
    report = build_report(scored, len(items), warnings, config, generated_at)
    md_path, json_path = save_outputs(scored, report, config, generated_at)

    print(f"[DONE] Markdown: {md_path}")
    print(f"[DONE] JSON: {json_path}")

    if args.push:
        webhook = os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
        if webhook:
            send_feishu_text(webhook, report)
            print("[DONE] Feishu pushed")
        else:
            print("[WARN] --push requested but FEISHU_WEBHOOK_URL is empty")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
