# BettaFish（微舆）本机部署说明

部署时间：2026-10-21
部署方式：源码部署（非 Docker 全量镜像），数据库用 Docker 容器
项目根目录：`C:\code\10gitbub群聊\BettaFish-main\BettaFish-main`

---

## 一、当前运行状态

| 组件 | 地址 | 状态 |
| :--- | :--- | :--- |
| 主应用（Flask） | http://localhost:5000 | ✅ 运行中 |
| InsightAgent | http://localhost:8501 | 按需启动（已实测可用） |
| MediaAgent | http://localhost:8502 | 按需启动 |
| QueryAgent | http://localhost:8503 | 按需启动 |
| ForumEngine | 无独立端口，由主应用内嵌 | 按需启动 |
| PostgreSQL 15 | 127.0.0.1:5444 | ✅ 运行中（容器 `bettafish-db`） |

数据库 28 张表已自动创建完毕。

---

## 二、启动与停止

### 启动数据库
```powershell
docker compose up -d db
```

### 启动主应用
```powershell
.\.venv\Scripts\python.exe app.py
```
然后浏览器打开 http://localhost:5000 ，在页面里点各引擎的「启动」按钮，
Streamlit 子应用才会真正拉起（默认它们是 stopped 状态，这是设计如此，不是故障）。

### 完整停止
```powershell
# 停主应用（占 5000/8501/8502/8503 的进程）
Get-NetTCPConnection -State Listen | Where-Object {$_.LocalPort -in 5000,8501,8502,8503} |
  Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force }
# 停数据库
docker compose down
```

### 重新初始化数据库表（一般不需要）
```powershell
.\.venv\Scripts\python.exe MindSpider\main.py --init-db
```

---

## 三、环境事实

- Python **3.12.10**（项目 venv：`.venv`，非 conda；本机没有 conda/uv）
- PostgreSQL 15 跑在 Docker，容器名 `bettafish-db`，映射 `5444->5432`
- 依赖已全部安装完毕，含 torch 2.14.1+cpu、transformers、sentence-transformers
- Playwright 浏览器 chromium-1248 已下载（爬虫用）
- MediaCrawler 深度爬虫子模块已从 GitHub 克隆并装好依赖
- 情感分析模型已预下载到 `SentimentAnalysisModel/WeiboMultilingualSentiment/model` 并实测推理正常
  （首次运行不会再卡在下载；模型基于 HF `tabularisai/multilingual-sentiment-analysis`，CPU 推理）

---

## 四、部署中修复的 4 个兼容性问题（重要，重装环境时会复现）

### 1. eventlet 0.33.3 与 Python 3.12 不兼容
- 现象：`AttributeError: module 'ssl' has no attribute 'wrap_socket'`，`app.py` 直接启动失败
- 原因：`ssl.wrap_socket` 在 Python 3.12 已被移除，eventlet 0.33.3 仍在调用
- 处理：升级到 `eventlet 0.41.3`

### 2. numpy 版本与 torch 的 DLL 冲突
- 现象：`OSError: [WinError 1114] Error loading "torch\lib\c10.dll"`
- 原因：torch 2.14 是按 numpy 2.x ABI 构建的，装 numpy 1.26.4 时 c10.dll 初始化失败
  （且 pyarrow 26 也强制要求 numpy>=2.0）
- 处理：保持 `numpy==2.5.4` + `pyarrow==26.0.0`
- 已知无害告警：streamlit 1.28.1 的元数据写着 `numpy<2`，pip 会提示冲突，实测运行正常

### 3. MediaCrawler 子模块为空
- 现象：`MindSpider/DeepSentimentCrawling/MediaCrawler` 是空目录（本项目是 zip 下载，没有 .git）
- 处理：`git clone --depth 1 https://github.com/NanmiCoder/MediaCrawler.git` 到该路径，
  再 `pip install -r` 它的 requirements.txt

### 4. MediaCrawler 依赖把一批库升级了
升级后已重新验证主应用与 Streamlit 子应用均正常，当前关键版本：
`pydantic 2.14.1 / sqlalchemy 2.1.5 / matplotlib 3.11.2 / pandas 2.2.3 / pillow 13.0.0 / playwright 1.64.0`

---

## 五、仍需你处理的重点事项

### 🔴 A. 联网搜索 Key（必需，否则分析会缺数据）
`.env` 里 `ANSPIRE_API_KEY` 还是空的。系统默认搜索工具是 Anspire：
- 申请：https://open.anspire.cn/
- 拿到后填 `ANSPIRE_API_KEY=xxx`，重启 app.py 即可
- 若改用博查：`SEARCH_TOOL_TYPE=BochaAPI` 并填 `BOCHA_WEB_SEARCH_API_KEY`

### 🔴 B. 平台登录（只有做「深度爬取」才需要）
MediaCrawler 抓取微博/小红书/抖音/快手/贴吧/知乎/B站时，需要扫码/短信登录。
首次运行会弹出浏览器窗口让你人工登录，登录态会被缓存。
注意：爬虫会启动真实浏览器，不是无人值守的。

### 🟡 C. PDF 导出（可选）
当前缺少 Windows GTK3 运行时，PDF 导出不可用（HTML/Markdown 报告不受影响）。
要用 PDF 就装 GTK3 Runtime 并把其 bin 目录加进 PATH。

### 🟡 D. 报告质量
报告由 `deepseek-chat` 生成。README 提醒：Report Agent 需要较强模型能力，
若最终报告出现图表空白，可把 `REPORT_ENGINE_*` 换成更强的模型。

---

## 六、已实测跑通的链路

用仓库自带的三份「武汉大学」样例分析报告作输入，跑了一次 ReportEngine 完整链路
（模板选择 → 文档布局 → 篇幅规划 → 6 个章节逐章生成 → 图表校验 → HTML 渲染）：

- 耗时 220 秒，产出 2.27 MB HTML 报告，5 张图表全部通过校验
- 报告标题：《珞珈山舆情全景：百年名校的骄傲、焦虑与烟火气》
- 产物：`final_reports/final_report_武汉大学舆情分析_20261022_103323.html`
  （同目录还生成了 IR JSON 与 state JSON）
- 复现命令：`.\.venv\Scripts\python.exe _run_report_demo.py`

### ⚠️ 重要：没有数据源时模型会「编造数据」

`insight_engine_streamlit_reports/deep_search_report_关于鹿晗的舆情_20261021_191630.md`
这份报告声称「八大平台 62.8 万条有效文本」，而数据库各表实际是 **0 行**。
InsightEngine 的检索走的是**本地数据库**，库空时它不报错，而是让大模型自由发挥，
产出一份看起来非常专业、数据却全是虚构的报告。

**在没跑爬虫（或没有搜索 API）之前，任何分析结论都不要采信。**
判断方法：跑完后查数据库 `select count(*) from weibo_note;` 等表，0 行就是没数据。

---

## 七、2026-10-22 第二次实测：话题提取

```powershell
cd MindSpider
..\.venv\Scripts\python.exe main.py --broad-topic --keywords-count 20
```

结果：
- 新闻源 12 个，成功 9 个（今日头条/抖音热榜/澎湃新闻 请求超时，属聚合站波动，重跑即可）
- 入库 `daily_news` **213 条真实热搜**，`daily_topics` 1 条（含 20 个关键词 + 每日总结）
- 关键词已写入 `MindSpider/data/daily_keywords.txt`，供深度爬取使用

### ⚠️ 但注意：这批数据的 `description` 字段**全部为空**

查库验证：
```sql
select source_platform, count(*), max(length(coalesce(description,'')))
from daily_news where crawl_date=current_date group by source_platform;
```
所有 9 个源的最大描述长度都是 **0**。

也就是说库里有的是「热搜标题 + 链接」，**没有正文、没有评论**。
这种数据量下跑 InsightAgent，它依然会自己编样本量和情感占比 —— 所以**不要**指望
只用 `--broad-topic` 就能出真报告。

要拿到真实正文与评论，必须跑深度爬取：
```powershell
cd MindSpider
..\.venv\Scripts\python.exe main.py --deep-sentiment --platforms wb xhs dy
```
这一步会打开真实浏览器要求你**扫码/短信登录**，无法无人值守。

---

## 八、2026-10-22 第三次实测：搜索 Key 探测与 MediaEngine 真实跑通

### 1. Key 归属判定（探测结果）

用户提供的 `sk-723e4f...` 未注明厂商，对三个端点实测：

| 端点 | 结果 | 结论 |
| :--- | :--- | :--- |
| Anspire `/api/ntsearch/search` | 401 The current request is not authorized | 不是 Anspire 的 Key |
| Tavily `/search` | 401 missing or invalid API key | 不是 Tavily 的 Key |
| 博查 `/v1/ai-search` | 403 You do not have enough money or package quota | **Key 有效，但无 AI Search 套餐** |
| 博查 `/v1/web-search` | **200 + 真实结果** | ✅ 可用（基础网页搜索额度） |

结论：这是**博查**的 Key，只能用**基础网页搜索**端点，不能用 AI Search 端点。

### 2. 必需的代码适配（已改）

`MediaEngine/tools/search.py` 做了两处修改，否则博查 web-search 会「静默返回空结果」：

1. `_parse_search_response`：原代码只解析 AI Search 的 `messages` 数组；
   新增对 `data.webPages.value` 结构的解析（该端点没有 messages）。
2. `_search_internal`：当 base url 含 `web-search` 时，剔除它不认识的
   `stream`/`answer` 参数，改为 `summary=True`，否则拿不到 snippet。

`.env` 对应改为：
```ini
SEARCH_TOOL_TYPE=BochaAPI
BOCHA_BASE_URL=https://api.bocha.cn/v1/web-search
BOCHA_WEB_SEARCH_API_KEY=sk-...
```

### 3. MediaEngine 真实跑通

```powershell
.\.venv\Scripts\python.exe _run_media_demo.py   # 主题：中国体操女团时隔20年重夺世锦赛女团冠军
```

- 4 个段落 × (1 次首搜 + 2 次反思) = 12 次真实网页搜索，全部命中当天真实新闻
- 博查返回的报道来自央视网、凤凰网、封面新闻、懂球帝等，日期均为 2026-10-22
- 产出：`media_engine_streamlit_reports/deep_search_report_中国体操女团时隔20年重夺世锦赛女团冠军_20261022_104957.md`（30 KB）

**这是本项目第一次产出「数据有真实来源」的分析报告。**

### 4. 仍然缺的：QueryEngine 只支持 Tavily

`QueryEngine/agent.py:44` 硬编码 `TavilyNewsAgency`，没有博查/Anspire 分支。
想让 QueryAgent 也跑起来，需要一个 **Tavily Key**（免费额度 1000 次/月，https://tavily.com ）。

### 5. 踩到的坑：页面上的「关闭系统」按钮会杀掉整个后端

主应用右下角有「关闭系统」按钮，点击会 POST `/api/system/shutdown`，
把所有 Streamlit 子进程和 Flask 一起停掉。验证期间被点过一次导致服务全停。
要停单个引擎请用各引擎自己的「停止」按钮。

---

## 九、配置文件

- 唯一配置文件：项目根目录 `.env`（已被 .gitignore 忽略）
- 7 个 Agent 目前全部指向 DeepSeek：`https://api.deepseek.com` + `deepseek-chat`
- 想给某个 Agent 换模型，只改对应那三行 `*_API_KEY / *_BASE_URL / *_MODEL_NAME`
