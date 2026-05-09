# insdaily 选题雷达

这套改造保留原 TrendRadar 项目，用一个独立脚本把公开素材源整理成公众号选题候选。

## 运行

```bash
uv sync --frozen --no-dev
uv run python scripts/insdaily_topic_radar.py
```

输出位置：

```text
output/insdaily/YYYY-MM-DD/HH-MM-topic-report.md
output/insdaily/YYYY-MM-DD/HH-MM-topic-report.json
```

推送到飞书：

```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/..."
uv run python scripts/insdaily_topic_radar.py --push
```

## 当前自动化源

已经接入并验证可读：

- 香港01 新闻 sitemap
- E! News Top Stories RSS
- Us Weekly RSS
- Entertainment Tonight RSS
- ETtoday 星光云 RSS
- Soompi RSS
- Vogue RSS
- HELLO! RSS
- Mail Online News RSS
- Daily Mail Showbiz RSS
- Page Six RSS
- Koreaboo RSS
- TMZ RSS
- Harper's Bazaar RSS
- Hypebae RSS
- Vanity Fair RSS
- Dazed RSS
- Refinery29 RSS
- Bustle RSS
- Metro UK RSS
- Cosmopolitan RSS
- Glamour RSS

这些源按用途分三层：

- A 档每日主源：HK01、E!、Us Weekly、ET、ETtoday、Soompi、Vogue、HELLO!、Mail Online、Daily Mail Showbiz、Page Six。适合找稳定高频选题：人物故事、娱乐时尚、港台日韩欧美明星、海外社会和华人可读的人情故事。
- B 档辅助源：Koreaboo、TMZ、Harper's Bazaar、Hypebae、Vanity Fair、Dazed、Refinery29、Bustle、Metro UK、Cosmopolitan、Glamour。适合找爆点、标题角度、女性情绪和流量嗅觉，争议事实要二次确认。
- C/D 档备选源：Reddit、The Sun、BuzzFeed、Guardian、NYT、Town & Country 等已经保留在配置里，但默认关闭。它们更适合作为社媒信号、背景核验或特定专题补充，不直接进入每日候选池。

People、The Cut、W Magazine、Kstyle、三立娱乐、中时娱乐、Google Trends、TikTok Creative Center、Pinterest Trends、Reddit 关系类社区等已保留在配置里，但当前没有稳定公开 RSS，或网络访问容易被拦，所以先禁用。后续可以通过代理、内部浏览器、付费监测服务、第三方 RSS、Reddit API 或专门抓取器再接入。

微信公号源无法像 RSS 一样公开抓取，所以暂时作为“中文表达和角度参考源”进入选题库：

槽值、谈心社、她刊、最人物、英国报姐、英国那些事儿、INSIGHT视界、留学生大叔、Vista氢商业、三联生活实验室、普象工业设计小站、不相及研究所、beebee星球、那个NG、女神汇、凤凰WEEKLY。

## 选题库方向

脚本会按这些方向给素材打分：

- 海外社会/反常识故事
- 明星娱乐/红毯时尚
- 女性/亲密关系/情绪
- 英国/留学/海外生活
- 人物故事/命运转折
- 消费/生活方式/产品
- 网感奇闻/社媒话题

每条候选会输出：

- 选题方向
- 来源、时间、链接
- 推荐角度
- 对标参考公众号
- 命中关键词和分数依据
- 备选标题

## 可以给你们的 4 种打法

1. 快反流量款  
   用 E!、Us Weekly、ETtoday、Page Six、Daily Mail、TMZ、HK01 娱乐和韩娱源做短平快。适合当天要发、要轻、要抓眼。

2. 女性共鸣款  
   用 Bustle、Refinery29、Cosmopolitan、Glamour、关系、婚恋、年龄焦虑、家庭冲突、人物处境做中长文。适合她刊、谈心社、槽值式包装。

3. 英国/留学信息差  
   用 Mail Online、Metro UK、HK01 的英国政策、留学、王室和海外生活素材，做“中文圈不知道但很该知道”的题。

4. 消费生活观察  
   用 Vogue、Harper's Bazaar、Hypebae、Dazed、Cosmopolitan、Glamour、香港01生活类内容，做年轻人消费、审美和生活方式变化。

## 调整方法

主要改这里：

```text
config/insdaily_sources.yaml
```

常用调整：

- 新增 RSS：在 `sources` 里加 `type: rss`
- 新增 sitemap：在 `sources` 里加 `type: sitemap`
- 调整选题偏好：改 `topic_groups` 的 `keywords`、`priority` 和 `angle`
- 调整输出数量：改 `app.top_n`
- 调整新鲜度：改 `app.freshness_days`
