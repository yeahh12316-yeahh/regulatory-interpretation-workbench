# 外规解读 Agent 项目交接记录与待办事项

更新时间：2026-08-22  
用途：开启新会话后，直接读取本文件继续工作，不重复已经完成的开发。

## 1. 项目目标

开发一个真实可用、可以公开分享的“外规解读 Agent”网站。用户从浏览器进入网站后，可以：

1. 不注册、不登录，直接进入公开工作台；
2. 选择金融机构类型；
3. 上传一份或两份法规原文；
4. 获得适用性判断、条款拆解、监管规则抽取、整体解读、逐条解读、新旧规比较和 Evidence 证据链；
5. 查看 HTML 交付页面；
6. 下载与 HTML 内容一致的 Word 报告；
7. 在需要时由人工复核、退回、修改、锁定和发布；
8. 全流程不要求开发者手工运行脚本。

产品范围只包括外规识别、适用性、条款拆解、监管要求、解读、版本比较、证据链、审核和交付物。不扩展到制度映射、Gap 分析、整改方案、控制设计或审计闭环。

## 2. 已确认的产品边界

### 2.1 公开访问方式

- 网站面向所有人公开分享。
- 前端不得出现登录页、注册页或强制登录入口。
- 用户打开网站后，系统自动为当前浏览器创建隔离的匿名工作空间。
- 匿名令牌只保存在当前浏览器，其他浏览器不会自动看到该工作空间。
- 后端仍保留 JWT、机构空间和角色权限代码，用于后续私有部署或多人协同，但不能阻塞公开版的基本使用。
- 不得改回“所有访客共享同一个公开机构空间”的实现，因为那会导致不同用户互相看到或修改数据。

### 2.2 法规和验收边界

- 当前验收法规：2017 年《金融企业呆账核销管理办法》及用户提供的 PDF。
- 用户已人工确认文号：`财金〔2017〕90号`。
- 当前实际验收 PDF 为 4 页，正文覆盖第一条至第二十五条。
- 当前 PDF 不包含附1、附2、附3正文；涉及附件的内容必须显示“附件待补充/待人工确认”，不得推断。
- 尚未提供可核验的 2015 年旧规全文，因此 S5 新旧规比较必须保持跳过或待补充状态，不得生成伪造比较结果。
- 任务目标是外规解读，不把当前结果包装成法律意见或正式监管结论。

### 2.3 页面边界

页面必须保持已确认的三栏工作台结构：

- 顶部全局栏；
- 左侧任务列表和法规目录；
- 中间法规内容、Workflow、解读和审核区域；
- 右侧 Evidence 证据链。

视觉基线：黑色顶部栏和左侧导航、白色内容区、德勤绿色交互和状态标识、德勤白色 Logo。不要为了增加登录、注册或机构切换而改变三栏结构。

## 3. 原始 22 项开发清单及当前状态

这里的“已完成”指工程实现或页面实现已经完成；“完全闭环”还需要真实数据、人工复核、公开端到端测试或生产验收时，会在说明中明确标出。

| 项目 | 内容 | 当前状态 |
|---|---|---|
| 1 | 冻结机构类型、适用范围、产品边界和发布口径 | 已完成。只做外规解读，保留机构类型选择，正式发布必须人工确认。 |
| 2 | 确定验收法规、旧规/新规样本和人工 Gold 标准 | 部分完成。2017 年正文 Gold 基线、12 个高风险事实点、数字字段和证据位置已建立；文号已人工确认；附1—附3和2015年旧规仍缺失。 |
| 3 | 冻结信息架构、用户流程、页面线框、视觉系统和交互规范 | 已完成。三栏工作台结构已冻结。 |
| 4 | 完成 HTML 阅读页、Word 报告和新旧规比较样式 | 已完成。已明确显示旧规缺失时不生成比较结论。 |
| 5 | 冻结技术架构、模型 Provider、存储、数据库、队列和部署方式 | 已完成。React+Vite、FastAPI、PostgreSQL、Redis、Celery、MinIO/S3、可替换模型 Provider、Docker Compose 和 Render 方案已确定。 |
| 6 | 建立代码仓库、开发环境、CI、Docker 和健康检查 | 已完成。CI、Dockerfile、Compose、Makefile、`/health`、`/ready`、Worker 心跳均已建立。 |
| 7 | 建立数据库、版本模型、证据模型、任务状态和审计日志模型 | 已完成。SQLAlchemy、Alembic、任务/法规/版本/条款/Requirement/Interpretation/Evidence/QC/AuditLog 等模型已建立。 |
| 8 | 登录、机构空间、角色权限和任务访问控制 | 后端完成，公开前端按确认要求不展示登录。JWT、机构和角色代码保留；公开版使用浏览器级匿名 Guest Workspace。公开多人隔离仍需端到端验证。 |
| 9 | 法规上传、文件存储、文本提取、页码定位和 OCR 兜底 | 工程实现完成，公开端到端仍需验证。已支持 PDF、SHA-256、pypdf、Poppler、Tesseract、OCR 页标记、原文件保留和失败重试。 |
| 10 | 机构类型选择、适用性规则和 S1 元数据识别 | 已完成工程实现。 |
| 11 | S2 法规定位、适用范围和版本关系识别 | 已完成工程实现。 |
| 12 | S3 条款拆解、监管规则抽取和结构化数字识别 | 已完成工程实现。 |
| 13 | S5 新旧规比较 | 工程实现完成，但当前因没有可核验 2015 年旧规而安全跳过；真实比较仍未完成。 |
| 14 | S4 整体解读、逐条解读和变化解读 | 已完成工程实现；变化解读依赖 S5，旧规缺失时不生成。 |
| 15 | Evidence 链路、Content Package 和人工锁定版本 | 工程实现完成；CASE-001 尚未完成人工逐项复核和 `HUMAN_LOCKED` Content Package 锁定。 |
| 16 | 规则 QC、LLM Reviewer、人工审核、退回、修改和发布闸门 | 工程实现完成；规则 QC 会阻断未复核内容，真实 LLM Reviewer 尚未完成有效调用验证。 |
| 17 | Workflow、异步任务、进度、失败恢复和节点重跑 | 本地/准生产工程实现完成；Render 免费公开版采用 API 内联执行，公开环境的失败恢复、重跑和长任务仍需验证。 |
| 18 | 首页、任务页、Workflow、解读、条款、比较、审核和报告中心 | 已完成页面实现。 |
| 19 | HTML Renderer、Word Renderer、下载和一致性检查 | 已完成工程实现并有测试；正式导出仍受人工锁定和发布闸门控制。 |
| 20 | Benchmark、端到端、权限、安全和回归测试 | 自动化 Benchmark 和回归测试已通过；公开浏览器真实上传、跨用户隔离和安全测试尚未完全关闭。 |
| 21 | 准生产部署、PostgreSQL、Redis、Worker、备份、日志、监控和模型 API | 基础公网部署已完成；Render 免费版的备份恢复、持久化、监控验收和真实模型 API 仍未完成。 |
| 22 | 真实法规和人工审阅验收，修复阻断后正式发布 | 未完成。CASE-001 当前必须保持 `NOT_RELEASED`，不能把演示结果当正式交付物。 |

按“公开可用 + 正式交付闭环”口径，目前仍有 10 个未完全关闭的项目：

`2、8、9、13、15、16、17、20、21、22`。

其中第 8、9、17、20、21 的工程代码大部分已经存在，剩余主要是公开环境实测、隔离验证、故障恢复、备份和生产验收，不应重复从零开发。

## 4. CASE-001 当前真实结果

CASE-001 是 2017 年金融企业呆账核销管理办法任务，当前真实工程链路已经产生：

- PDF 页数：4 页；
- 正文条款：25 条；
- Requirement：56 条；
- 逐条 Interpretation：25 条；
- 整体 Interpretation：1 条；
- 因此 Interpretation 数据对象按“逐条 + 整体”口径为 26 个；旧验收报告中的 25 个是只统计逐条解读；
- Evidence：25 条；
- S1、S2、S3、S4：已完成；
- S5：`skipped`，原因是没有可核验的2015年旧规；
- 规则 QC：发现 109 个发布阻断项；
- LLM Reviewer：`not_configured`，没有冒充已经完成模型复核；
- 当前正式发布状态：`NOT_RELEASED`。

正式发布前需要：

1. 在审核页保存用户确认的 `财金〔2017〕90号` 和审计记录；
2. 对附1—附3：如果没有完整官方原文，继续保留“待补充”状态；如果要解读附件，上传附件正文或完整官方文件；
3. 人工逐项核对 56 条 Requirement；
4. 人工核对 25 条 Evidence 的原文、页码、行号和文件哈希；
5. 人工复核并锁定 25 条逐条 Interpretation + 1 条整体 Interpretation；
6. 重新运行规则 QC；
7. 如配置模型，再运行 LLM Reviewer，并由人工判断其发现项；
8. 生成 `HUMAN_LOCKED` Content Package；
9. 只有闸门通过后才允许正式导出和发布。

## 5. 当前代码和验证状态

### 5.1 Git 状态

- GitHub 仓库：`https://github.com/yeahh12316-yeahh/regulatory-interpretation-workbench`
- 当前工作分支：`codex/render-free`
- 当前分支与 `origin/main` 对齐；工作树在本次交接前干净。
- 最新公开代码提交：`d580044 fix: restore no-login anonymous workspaces`
- 该提交实现了公开匿名 Guest Workspace，并取消了公开版登录界面。

### 5.2 本地验证记录

上一次完整验证结果：

- `./.venv/bin/pytest -q`：39 passed；
- `tests/backend/test_regulation_ingest.py -q`：7 passed；
- `pnpm run build`：通过；
- Docker/Compose、Alembic、健康检查、Worker 和前端构建均已有验证记录；
- 旧准生产 CASE-001 验收报告记录为 37 passed，这是新增 Guest endpoint 测试前的历史数字，不要与当前 39 passed 混淆。

### 5.3 重要文件

- 产品边界：`docs/PRODUCT_SCOPE.md`
- 当前实现状态：`docs/IMPLEMENTATION_STATUS.md`
- CASE-001 验收：`docs/ACCEPTANCE_REPORT_2026-08-22.md`
- 验收材料：`docs/ACCEPTANCE_MATERIALS_CASE_001.md`
- 公网部署：`docs/PUBLIC_DEPLOYMENT.md`
- 准生产部署：`docs/PREPROD_DEPLOYMENT.md`
- 架构决策：`docs/ARCHITECTURE_DECISIONS.md`
- 页面信息架构：`docs/INFORMATION_ARCHITECTURE.md`
- 视觉系统：`docs/WEBSITE_STYLE_SYSTEM.md`
- 前端入口：`src/App.jsx`
- API 客户端：`src/lib/api-client.js`
- 前端运行时配置：`src/lib/runtime-config.js`
- 后端入口：`backend/app/main.py`
- 上传解析：`backend/app/api/ingest.py`
- LLM Reviewer：`backend/app/services/llm_reviewer.py`
- Render 配置：`render.yaml`

## 6. 当前公网部署状态

### 6.1 前端

- 公网地址：
  `https://yeahh12316-yeahh.github.io/regulatory-interpretation-workbench/`
- GitHub Pages Workflow：`Deploy frontend workbench to GitHub Pages`
- 最新已验证成功的发布：Run #23，提交 `d580044`：
  `https://github.com/yeahh12316-yeahh/regulatory-interpretation-workbench/actions/runs/32578723608`
- GitHub Actions Repository Variable 已存在：
  `VITE_API_BASE_URL=https://regulatory-interpretation-api.onrender.com/api`
- 公开构建产物已经确认实际包含 Render API 地址，不是相对路径 `/api`。

### 6.2 后端

- Render API：
  `https://regulatory-interpretation-api.onrender.com`
- `/health` 已验证返回：`status=ok`；
- `/ready` 已验证返回：`status=ready`、PostgreSQL connected、Redis connected；
- `POST /api/auth/guest` 已验证返回成功，并产生匿名访问令牌；
- GitHub Pages Origin 的 CORS preflight 已验证通过；
- Render 免费部署当前采用 API 内联 Workflow，不是独立公网 Worker。

### 6.3 免费部署限制

- Render Web Service 空闲后会休眠，首次请求可能需要等待；
- Free PostgreSQL 存在容量和生命周期限制；
- Free Key Value/Redis 不持久化；
- 免费 Web Service 没有持久化磁盘；
- 上传文件和报告存于临时文件系统，重启或休眠后可能丢失；
- 当前架构适合公开验证，不应被称为稳定生产系统；
- 不要上传真实客户资料、敏感法规或需要长期保存的正式材料。

## 7. 最近发现的公网问题

用户在 Safari 中看到上传弹窗错误：`Load failed`。

目前已完成的检查：

1. GitHub Actions 的 `VITE_API_BASE_URL` 配置正确；
2. 公开 JavaScript 构建产物中已写入 Render API 地址；
3. Render `/health` 和 `/ready` 正常；
4. GitHub Pages 到 Render 的 CORS 预检正常；
5. Guest endpoint 正常；
6. 重新打开公开网站后，上传弹窗本身可以正常加载，没有登录界面。

当前判断：截图中的错误更可能是 Safari 旧缓存或 Render 免费实例唤醒期间的瞬时网络失败，尚未用用户的真实 PDF 在公网重新执行完整上传。不要直接声称“真实公网上传已验收通过”。

用户下一次重试步骤：

1. 关闭上传弹窗；
2. Safari 按 `Option + Command + R` 强制刷新；
3. 等待 Render 免费实例唤醒，必要时等待 30—60 秒；
4. 重新打开“上传法规”，选择 PDF，再点击“上传并登记”。

如果仍然失败，下一步应在用户明确同意将该 PDF 上传到公网 Render 后，完成一次真实上传端到端测试，并同时查看 Render 日志中的 `/api/regulations/import` 请求。没有用户明确授权，不要把用户的完整法规 PDF 发往公网做测试。

## 8. LLM API 配置状态

用户提供过以下配置意图：

- Provider：OpenAI-compatible；
- Base URL：`https://nova.deloitte.com.cn/del/v1/chat/completions`；
- Model：`DeepSeek-V4-Flash`；
- API Key：用户曾在聊天和本地 `.env.local` 中提供过。

安全边界：聊天中出现过的 API Key 不应继续使用，必须撤销并重新生成。绝不能把 API Key 放入 GitHub Pages、GitHub Actions Variable、前端 JavaScript、截图或交接文件。

正确配置位置：Render Dashboard → `regulatory-interpretation-api` → Environment → `LLM_API_KEY`，保存后重新部署。`render.yaml` 已将 `LLM_API_KEY` 设置为 `sync: false`，不会把密钥提交到仓库。

代码会自动处理两种 Base URL：如果地址已经以 `/chat/completions` 结尾，就直接请求；否则自动追加 `/chat/completions`。模型配置需要同时满足 Provider、API Key 和 Model 非空，之后再运行 LLM Reviewer 验证真实返回。当前不能把“本地文件已填写”当成“Render 生产环境已配置”。

## 9. 新会话继续开发的严格顺序

### 第 1 步最新进展（2026-08-22）

- Render 公网匿名 API 已用项目内 2017 年版 PDF 完成真实上传、解析和 S1—S4；结果为 4 页、25 条款、56 条 Requirement、25 条逐条 Interpretation、25 条 Evidence，S5 安全跳过。
- GitHub Pages 浏览器层已完成“选择 PDF → 上传并登记 → 显示 4 页/25 条款/哈希 → 运行 S1—S4 → Workflow 100% → 显示 56 条要求/25 条解读”的验证。
- 发现网页刷新后任务列表仍为静态数据的问题，已新增 API 任务列表、当前任务 ID 持久化和刷新后的 Workflow/解读恢复逻辑；对应测试为 `tests/frontend/task_persistence.test.mjs`。
- 修复后的本地验证为：前端持久化测试 2 passed、后端 39 passed、Benchmark 6 cases / 20 assertions / 0 asset errors、前端生产构建通过。
- GitHub Actions CI 已通过：提交 `8c40ccd` 的 backend-worker、frontend、compose-smoke 全部成功；Pages 已发布新构建 `assets/index-DZ7LCuZf.js`。
- 发布后的公网页面已强制刷新验收：真实任务列表恢复为 1 个任务，Workflow 恢复为 100%，S1—S4 为 completed，S5 为 skipped，56 条要求、25 条逐条解读和“待人工复核”均恢复。第 1 步正式关闭。

新会话不要重复实现第 1—19 项，也不要先做页面重设计。建议顺序如下：

### 待办 1：关闭公网上传验证阻塞

- 先让用户按强制刷新和等待唤醒后重试；
- 若仍失败，取得用户明确同意后，用真实 PDF 做一次公网上传测试；
- 查 Render 请求日志，区分 CORS、冷启动、上传、解析和临时存储问题；
- 必要时修复前端网络错误提示、重试机制或后端上传处理；
- 通过真实浏览器上传、解析、任务创建和页面刷新验证。

### 待办 2：完成 CASE-001 人工验收资料闭环

- 保存 `财金〔2017〕90号` 的用户确认和审计记录；
- 保存附1—附3“未提供/待补充”的明确状态；
- 明确 Interpretation 的统计口径：25 条逐条 + 1 条整体；
- 逐项复核 Requirement、Interpretation、Evidence；
- 重新运行 QC，确认阻断项变化。

### 待办 3：决定是否补齐旧规并启用 S5

- 如果没有2015年旧规官方全文，保持 S5 `skipped`；
- 如果用户提供完整、可核验的2015年旧规，登记文件哈希、版本关系和来源定位；
- 再运行 S1—S3、S5、S4；
- 不得因为页面需要展示比较而伪造旧规内容。

### 待办 4：完成人工锁定 Content Package

- 审核页完成全部人工修改或确认；
- 锁定 56 条 Requirement、25 条逐条 Interpretation、1 条整体 Interpretation 和 25 条 Evidence；
- 生成 `HUMAN_LOCKED` Content Package；
- 记录 Content Package 版本、内容哈希、锁定人和锁定时间。

### 待办 5：配置并验证真实 LLM Reviewer

- 先撤销聊天中暴露的旧 API Key；
- 生成新 Key；
- 只把新 Key 填入 Render Secret `LLM_API_KEY`；
- 确认 `LLM_PROVIDER=openai_compatible`、Base URL 和 `LLM_MODEL=DeepSeek-V4-Flash`；
- 重新部署并在审核页运行 LLM Reviewer；
- 如果接口返回错误、非 JSON 或模型不支持 `response_format`，记录为失败/需人工处理，不能标记为通过。

### 待办 6：验证公开 Workflow、失败恢复和节点重跑

- 用公开浏览器创建新任务；
- 上传法规并运行 S1—S4；
- 验证进度、刷新恢复、失败状态、重试和节点重跑；
- 记录 Render 免费实例冷启动和长任务限制；
- 确认 API 内联执行不会被误称为独立 Worker 生产能力。

### 待办 7：完成公开端到端、隔离和回归测试

- 无登录直接打开；
- 两个浏览器分别创建匿名工作空间；
- 确认任务、法规和 Evidence 不互相可见；
- 验证 PDF 上传、解析、OCR、S1—S4、审核、HTML、Word 下载；
- 验证无 API、API 冷启动、401 过期、错误上传和重复刷新；
- 检查前端不泄露 LLM API Key。

### 待办 8：完成部署硬化

- 选择可长期保存的对象存储；
- 配置 PostgreSQL 定期备份；
- 完成备份恢复演练；
- 配置日志、监控、告警和限流；
- 评估是否迁移到有持久化磁盘和独立 Worker 的部署环境；
- 决定是否绑定自定义域名和 TLS。

### 待办 9：正式人工验收

- 用真实法规和人工审阅人员完成最终验收；
- 修复所有阻断项；
- QC 通过；
- LLM Reviewer 状态明确；
- Content Package 为 `HUMAN_LOCKED`；
- HTML/Word 一致性检查通过；
- 形成正式发布记录。

## 10. 新会话启动提示词

将以下内容复制到新会话开头：

> 请先读取项目目录 `/Users/yeahh/Documents/ChatGPT/外规解读agent/` 下的：
> `docs/HANDOFF_2026-08-22_PUBLIC_CONTINUATION.md`、
> `docs/IMPLEMENTATION_STATUS.md`、
> `docs/ACCEPTANCE_REPORT_2026-08-22.md`、
> `docs/PUBLIC_DEPLOYMENT.md`，并检查当前 Git 状态。
>
> 继续开发公开版外规解读 Agent。产品只做外规识别、适用性、条款拆解、S1—S5/S4 解读、Evidence、审核和 HTML/Word 交付，不做制度映射、Gap、整改或审计闭环。
>
> 重要边界：公开网站不显示登录界面，不要求注册；使用浏览器级匿名隔离工作空间。2017 年法规文号 `财金〔2017〕90号` 已由用户人工确认。当前 PDF 为4页正文，覆盖第一条至第二十五条，但不含附1—附3；没有2015年旧规时 S5 必须跳过，不得伪造比较结果。
>
> 当前公网地址：
> 前端 `https://yeahh12316-yeahh.github.io/regulatory-interpretation-workbench/`
> 后端 `https://regulatory-interpretation-api.onrender.com`
> 最新公开提交 `8c40ccd`，GitHub Pages 已成功发布，CI 与 Compose smoke 均通过。
>
> 现在不要重复第1—19项工程实现。先处理“公网上传出现 Load failed”的验证：先确认公开构建的 API 地址、CORS、Render `/health`、`/ready` 和 `/api/auth/guest`；让用户强制刷新后重试。如果需要把用户真实 PDF 上传到公网测试，必须先取得用户明确同意。然后按“CASE-001人工验收 → Content Package锁定 → LLM Reviewer → Workflow公开验证 → 端到端与部署硬化 → 正式人工发布验收”的顺序继续。

## 11. 重要禁止事项

- 不要恢复公开登录页或注册页。
- 不要让所有公开用户共享同一个机构空间。
- 不要把聊天中出现过的 API Key 写入仓库或交接文档。
- 不要把 GitHub Pages 前端可访问性称为完整后端生产可用。
- 不要把规则生成结果冒充 LLM Reviewer 结果。
- 不要在缺少2015年旧规时生成 S5 比较结论。
- 不要在缺少附1—附3原文时推断附件内容。
- 不要在人工复核和 Content Package 锁定前宣称 CASE-001 已正式发布。
- 不要未经用户明确授权把用户完整法规 PDF 上传到公网做测试。
