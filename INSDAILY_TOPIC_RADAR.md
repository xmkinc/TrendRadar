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

你们自己的账号矩阵会作为最终承接账号进入报告：

- `insdaily`：广谱海外热点、娱乐快反、英国/海外生活、可中文化的社会话题。
- `girldaily`：女性关系、情绪共鸣、审美/身材/年龄焦虑、消费生活方式。
- `insdaily人物`：明星或普通人的命运转折、人生故事、逆袭/塌房/复出/离世/病痛等人物线。

下面这些公众号不再作为“对标账号”输出，只作为素材源、网感源和中文表达参考：

槽值、谈心社、她刊、最人物、英国报姐、英国那些事儿、INSIGHT视界、留学生大叔、Vista氢商业、三联生活实验室、普象工业设计小站、不相及研究所、beebee星球、那个NG、女神汇、凤凰WEEKLY。

## 推送节奏

现在分两种模式：

- `daily`：新闻时效选题，每天/每天两次推送，飞书只发最值得当天看的短单。
- `weekly`：专题选题池，每周一次，适合周会讨论、人物长文、女性议题、消费审美和海外生活专题。

## 选题库方向

根据你发的 2023 年原创爆文库，80 条有效爆文里，主要结构是：

- 类型上：娱乐 31 条、人物 28 条、资讯 15 条、人文 6 条。核心不是硬新闻，而是“人物娱乐 + 女性情绪 + 可中文化的海外故事”。
- 阅读最高的钩子集中在：年龄/外貌反差、身材颜值变化、婚恋关系反转、童年记忆/旧人新事、公众审判式争议。
- 标题常见结构是“强人物标签 + 数字/反差 + 情绪判断 + 悬念追问”，例如近照、长大后、减肥、离婚、翻车、网友、全网、到底经历了什么。

所以雷达会先按内容方向匹配，再额外套一层“爆文库模型”加分：

- 年龄/外貌反差：适合 `insdaily` 和 `insdaily人物`
- 婚恋关系反转：适合 `girldaily` 和 `insdaily`
- 旧人新事/童年记忆：适合 `insdaily人物`
- 女性/家庭消耗：适合 `girldaily` 和 `insdaily人物`
- 全网围观/审判冲突：适合 `insdaily` 和 `girldaily`

基础内容方向仍保留这些：

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
- 建议账号：`insdaily`、`girldaily` 或 `insdaily人物`
- 评分拆解：信源、选题贴合、爆文结构、传播信号、时效、标题形态、风险扣分、弱选题扣分
- 命中关键词和分数依据
- 备选标题

## 评分逻辑

现在使用 `insdaily_khazix_v1` 分项评分，接近 100 分制：

- 信源：A/B/C/D 档和源权重共同决定，Daily Mail Showbiz、Page Six、HK01、E! 等主源会更稳。
- 选题贴合：看它命中哪个内容方向，以及命中的关键词密度。
- 爆文结构：额外识别爆文库里常见的年龄/外貌反差、婚恋反转、旧人新事、女性家庭消耗、全网围观。
- 传播信号：`reveals`、`responds to`、`pregnant`、`unrecognizable`、`backlash`、`官宣`、`回应`、`塌房` 等会加分。
- 时效：6 小时内最高，24 小时内次之，专题模式会放宽。
- 标题形态：数字、反差、悬念追问、公众围观、强情绪标点会加分。
- 风险扣分：政治敏感、自杀细节、未成年、法律指控、死亡、健康和减肥药等会扣分或提示复核。
- 弱选题扣分：quiz、sale、coupon、recap、live updates 等低改写价值内容会扣分。

## 可以给你们的 4 种打法

1. 快反流量款  
   用 E!、Us Weekly、ETtoday、Page Six、Daily Mail、TMZ、HK01 娱乐和韩娱源做短平快。优先找全网围观、明星关系、造型翻车、争议回应。

2. 女性共鸣款  
   用 Bustle、Refinery29、Cosmopolitan、Glamour、关系、婚恋、年龄焦虑、家庭冲突、人物处境做中长文。更贴近 `girldaily`：不是单纯八卦，而是“她为什么会被消耗/被审判/被理解”。

3. 英国/留学信息差  
   用 Mail Online、Metro UK、HK01 的英国政策、留学、王室和海外生活素材，做“中文圈不知道但很该知道”的题。

4. 消费生活观察  
   用 Vogue、Harper's Bazaar、Hypebae、Dazed、Cosmopolitan、Glamour、香港01生活类内容，做年轻人消费、审美和生活方式变化。

5. 人物命运转折
   用 People、Daily Mail、HELLO!、HK01、ET、Soompi/Koreaboo 等人物材料，找“昔日标签 + 今日变化 + 命运拐点”。更贴近 `insdaily人物`：旧人新事、童星长大、复出、病痛、离世、翻红、塌房、逆袭。

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
