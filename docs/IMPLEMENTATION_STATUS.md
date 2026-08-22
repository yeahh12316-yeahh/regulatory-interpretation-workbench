# 外规解读智能体工作台实施状态

更新时间：2026-08-22

## 当前步骤

第 1—15 项已完成工程实现；第 16 项已完成真实法规的准生产工程验收，但正式发布仍受人工复核、正式来源和公网生产环境闸门约束。本机 Docker Desktop、Docker Compose、PostgreSQL、Redis、Worker、MinIO 和 Prometheus 已运行。

| 步骤 | 状态 | 说明 |
|---|---|---|
| 第 1 步：冻结产品边界 | 已完成 | 面向多类型金融机构，只做外规识别、适用性、条款拆解、解读、证据和交付物 |
| 第 2 步：验收法规与 Gold | 已完成（正文 Gold 基线） | 已冻结 2017 年版正文第一条至第二十五条、页码、机构适用性、12 个高风险事实点、数字字段和证据位置；文号已由用户人工确认，附件仍作为后续 QC 的待确认边界 |
| 第 3 步：信息架构和流程 | 已完成 | 顶部栏、左侧任务/目录、中间解读、右侧证据链 |
| 第 4 步：页面实现与浏览验收 | 已完成 | 已完成黑色顶栏与左侧导航、Deloitte 官方白色 Logo、白底黑字、德勤绿交互、证据上传/定位及浏览器验收，并保存高保真原型图 |
| 第 5 步：技术架构冻结 | 已完成 | 已冻结 React+Vite 前端、FastAPI API、PostgreSQL、Redis+Celery、S3/MinIO、可替换模型 Provider、异步 Workflow 和 Docker Compose 部署边界 |
| 第 6 步：代码骨架、开发环境、CI、Docker 与健康检查 | 已完成 | 已建立 backend、worker、tests、Dockerfile、Compose、CI、Makefile、健康检查和 Worker 心跳；本地测试、Compose YAML、前端构建通过，GitHub Actions 已真实启动全栈 Compose 并通过 API/Web 健康检查 |
| 第 7 步：数据库、版本、证据、任务状态和审计日志模型 | 已完成 | 已建立 SQLAlchemy 领域模型、Alembic 首次迁移、PostgreSQL 真实连接、自动迁移和任务/法规/来源文件/证据最小 CRUD API，并通过本地与 GitHub Compose 验收 |
| 第 8 步：登录、机构空间、角色权限和任务访问控制 | 后端完成，前端后置 | 后端已实现注册/登录、JWT、当前用户、机构切换、成员管理、角色变更和任务组织隔离；按单团队私有部署目标，第一版前端不设置强制登录和顶部权限控件 |
| 第 9 步：法规上传、解析、版本登记与原文定位 | 已完成 | 已实现 PDF 上传、原文件哈希与私有存储、标题/文号/日期识别、版本登记、条款拆解、页码/行号定位、原文件访问接口和工作台上传入口 |
| 第 10 步：S1—S4 真实条款解读流水线 | 已完成 | 已实现 S1 元数据确认、S2 机构适用性、S3 监管要求抽取、S4 整体/逐条解读、Requirement/Interpretation/Evidence 持久化和工作台运行入口；默认规则生成并待人工复核 |
| 第 11 步：人工复核、质量检查与交付物导出 | 已实现第一版 | 已实现人工复核 API/UI、原文和证据保护、审计留痕、QC 阻断闸门、Word 导出；真实法规验收结果见 `docs/ACCEPTANCE_REPORT_2026-08-22.md` |

## 用户确认开发顺序：第 15 项交付（准生产部署）

- 本机已安装并验证 Docker Desktop、Docker CLI 和 Docker Compose。
- `docker-compose.preprod.yml` 已编排 API、Web、PostgreSQL、Redis、Celery Worker、MinIO、Prometheus 和 PostgreSQL backup。
- API 提供 `/health`、`/ready`、`/metrics`；准生产就绪检查确认数据库和 Redis 已连接。
- API 和 Worker 镜像均包含跨容器工作流执行所需的代码；Worker 通过 Redis 消费 `workflow.execute`。
- Web 通过 Nginx 将 `/api/` 代理到 API；本机验证地址为 `http://127.0.0.1:18080/`。
- 配置模板、备份脚本、Prometheus 配置和部署说明分别位于 `.env.preprod.example`、`ops/backup-postgres.sh`、`ops/prometheus.yml` 和 `docs/PREPROD_DEPLOYMENT.md`。
- 当前仍是本机准生产环境，不等同于公网生产部署。

## 用户确认开发顺序：第 16 项交付（真实法规和人工验收）

- 真实 CASE-001 已完成 4 页 PDF 上传、25 条款解析、异步 S1—S4 执行、S5 安全跳过、56 条 Requirement、25 条 Interpretation 和 25 条 Evidence 生成。
- 规则 QC 以 109 个阻断项拦截正式发布；LLM Reviewer 明确返回 `not_configured`。
- 自动化回归为 37 passed；Benchmark 为 6 cases / 20 assertions / 0 asset errors；容器、Compose、API、Web 反向代理和数据库/队列就绪检查均通过。
- 正式发布尚未通过：文号已由用户确认但尚未写入正式任务审核记录，附1—附3缺失，Requirement/Interpretation/Evidence尚未完成逐项人工复核与锁定，LLM API Key 未配置，当前也不是公网生产环境。
- 完整验收证据见 `docs/ACCEPTANCE_REPORT_2026-08-22.md`。

## 第 4 步浏览验收证据

## 用户确认开发顺序：第 2 项交付（对应原清单第 4 步）

- HTML 阅读页：保留顶部栏、左侧任务/目录、中间内容、右侧证据链三栏工作台结构，补齐事实、监管要求、解读、证据和待确认边界的视觉层级。
- 版本比较页：新增“版本比较”标签，明确显示旧版权威原文尚未补充，当前不生成新旧规差异结论；不伪造 S5 结果。
- Word 报告：统一标题、绿色章节标识、元数据表、监管要求表、证据链和待确认边界；新增“六、版本比较”章节，与 HTML 页面保持相同的待补充口径。
- 字体与导出验收：使用 LibreOffice 转 PDF/PNG 复核 2 页 Word 测试报告，确认中文可读、表格无明显溢出、版本比较和证据边界均已呈现。
- 验证结果：前端生产构建通过；复核/DOCX 下载测试通过；全量后端与 Gold 测试通过；`git diff --check` 通过。

## 用户确认开发顺序：第 3 项交付（对应原清单第 9 步）

- 上传与存储：上传后先持久化原始 PDF、计算 SHA-256，并记录来源文件、任务、请求版本标签和解析检查点；解析失败不删除原文件。
- 文本提取：继续使用 `pypdf` 做文本型 PDF 提取；每页记录提取方法、字符数和可读状态。
- OCR 兜底：新增可选 OCR 适配器，使用 Poppler 渲染无文本页面、使用 Tesseract 识别，并把 OCR 页码写入 `extraction_summary`；OCR 页条款的 `source_offset` 标记为 `extraction_method=ocr`，后续必须人工核验。
- 失败恢复：新增 `POST /api/source-documents/{document_id}/retry-parse`；解析失败响应返回来源文件编号和重试地址，前端上传弹窗显示“文件已安全保存，可继续重试”。
- 防止伪成功：扫描 PDF 在 OCR 不可用或未形成任何条款时不会登记空版本，而是保持失败/可重试状态。
- 运行环境：`backend/Dockerfile` 已加入 `poppler-utils`、`tesseract-ocr`、中文和英文语言包；本机没有 Docker CLI，镜像构建仍需 GitHub Actions 或部署环境验收。
- 验证结果：全量后端测试 `18 passed`；前端生产构建通过；本地浏览器已验证上传弹窗展示 OCR、原文件保留和重试口径；无前端控制台错误；已在本机用真实 `/opt/homebrew/bin/pdftoppm` 和 `/opt/homebrew/bin/tesseract -l chi_sim+eng` 完成扫描型中文 PDF OCR，解析器识别 2 条条款并保留第 1 页及 `extraction_method=ocr` 证据。

- 页面名称：外规解读智能体工作台。
- 布局：顶部全局栏 + 左侧任务/法规目录 + 中间法规解读 + 右侧证据链。
- 颜色：顶部栏与左侧导航为黑底白字，内容区为白底黑字，证据轨道及交互统一使用德勤绿；DORA 示意数据已移除。
- 页面状态：明确显示“2017 年版已载入”“待解析”“版本比较待补充原文”。
- 已验证交互：标签切换、任务标题搜索、证据卡选择、侧栏目录展开/收起、操作反馈提示。
- 已验证交互：证据“查看定位”、 “添加证据”文件选择、左侧栏收起/展开均可用。
- 高保真原型图：`docs/prototypes/外规解读智能体工作台-v2.png`
- 本地预览地址：`http://127.0.0.1:5173/`

## 第 2 步边界

1. 本次非 S5 测试使用用户提供的 4 页 PDF，正文范围为第一条至第二十五条。
2. 三个附录不在当前文件中，涉及附录时必须停止并提示补充材料。
3. 2015 年修订版不作为本任务输入；未来启用 S5 时再单独补充。

本任务可以继续验证 2017 年版正文的解析、适用性、条款解读、证据链和页面交互；不得生成附录结论或新旧规比较结果。

## 第 5 步架构基线

- 架构决策：[docs/ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md)
- 配置模板：[.env.example](../.env.example)
- 前端运行时配置契约：[src/lib/runtime-config.js](../src/lib/runtime-config.js)
- 第 6 步开始建立 FastAPI、数据库、Worker 和真实 API，不在本步提前实现。

## 第 6 步工程验收证据

- 后端入口：`backend/app/main.py`
- Worker 入口：`worker/app/celery_app.py`
- Docker 编排：`docker-compose.yml`
- CI：`.github/workflows/ci.yml`
- 测试：`tests/backend/test_health.py`、`tests/worker/test_heartbeat.py`
- 验证结果：3 个测试通过；Python 编译通过；Compose YAML 解析通过；前端构建通过；GitHub Actions Compose smoke test 通过，已完成 API、Web 健康检查并清理容器。
- 环境说明：当前本机没有 Docker CLI，因此未在本机执行容器启动；GitHub-hosted Docker 验收已覆盖 Compose 构建、启动、API/Web 健康检查、PostgreSQL 迁移、CRUD 写入/读取和 teardown。Redis、MinIO 的业务联通和 Worker 消费逻辑仍属于后续开发范围。

## 第 7 步交付

- ORM 模型：`backend/app/db/models.py`
- 数据库基类与会话：`backend/app/db/base.py`、`backend/app/db/session.py`
- Alembic 配置与首个迁移：`alembic.ini`、`backend/migrations/versions/568020acaa60_initial_regulatory_interpretation_schema.py`
- 已覆盖对象：Task、SourceDocument、Regulation、RegulationVersion、Article、Requirement、Interpretation、Evidence、VersionRelation、QCResult、AuditLog，以及解释/要求与证据关联表。
- 验证结果：数据库领域模型 SQLite 集成测试通过；Alembic upgrade head、current、downgrade base 通过。
- 最小 API：`POST/GET /api/tasks`、`POST/GET /api/regulations`、`POST/GET /api/source-documents`、`POST/GET /api/evidence`；证据写入必须引用已存在的来源文件。
- 验收结果：GitHub Actions Compose smoke test 已执行 Alembic 迁移、`/ready` PostgreSQL 连通检查，以及任务—法规—来源文件—证据的真实写入/读取链路；[CI run](https://github.com/yeahh12316-yeahh/regulatory-interpretation-workbench/actions/runs/32499115706)。
- 当前边界：2015 年版本仍未提供，S5 不启用；本步不代表外规解读 Agent 已经可以调用模型生成真实解读。

## 第 8 步当前交付

- 认证：`backend/app/api/auth.py`、`backend/app/security.py`
- 机构与成员：`backend/app/api/organization.py`
- 角色：`owner`、`admin`、`editor`、`reviewer`、`viewer`
- 数据迁移：`backend/migrations/versions/b2f3fd094106_add_organizations_users_memberships_and_.py`
- 已验证：注册、登录、JWT Bearer 认证、多机构切换、成员添加、角色升级、viewer 只读、editor 可创建任务、跨机构任务不可见。
- 验收结果：[GitHub CI run](https://github.com/yeahh12316-yeahh/regulatory-interpretation-workbench/actions/runs/32500761887)。
- 前端调整：按单团队内部使用/私有部署目标，第一版直接进入工作台，移除强制登录、机构空间入口、预览用户和顶部权限控件；后端认证和权限代码保留，后续需要多人协同或公网部署时再启用。
- 布局修复：三栏固定为左侧任务/目录、中间解读、右侧证据链；压缩顶部工具栏最小宽度，避免按钮换行和证据区被挤压。
- 当前边界：第十步已完成；第十一步已进入人工复核和 QC 实现阶段。

## 第 9 步交付

- 上传接口：`POST /api/regulations/import`，支持 PDF、文件哈希、来源地址、版本标签和可选任务绑定。
- 解析服务：`backend/app/services/regulation_ingest.py`，使用 `pypdf` 提取页面文本，识别法规标题、文号、发布日期、生效日期、版本标签和“第×条”条款。
- 版本登记：自动创建 `SourceDocument`、`Regulation`、`RegulationVersion` 和 `Article`；同一法规的现行版本会保留 `previous_version_id`，不会覆盖原版本。
- 原文定位：每个条款保存 `source_page` 与 `source_offset`（页码、起止行），并提供条款列表、单条查询和原文件访问接口。
- 私有部署：设置 `PRIVATE_MODE=true` 后，内网单团队可不经过登录页面直接调用 API；公网部署不得开启该模式。
- 前端入口：左侧任务区新增“上传法规”，未配置 API 时明确禁用真实提交，不伪造上传成功；配置 `VITE_API_BASE_URL` 后进入真实上传/解析结果页。
- 验收结果：[GitHub CI run](https://github.com/yeahh12316-yeahh/regulatory-interpretation-workbench/actions/runs/32505000085)；公开 Pages 已更新并验证上传入口。
- 当前边界：第十步已承接本步登记结果；公开 Pages 未连接后端时不会伪造运行成功。

## 第 10 步交付

- 流水线服务：`backend/app/services/interpretation_pipeline.py`，按 `S1 → S2 → S3 → S4 → S5` 记录结果；当前 CASE-001 因未提供 2015 年核验旧版，S5 按闸门明确跳过。
- S1 元数据确认：输出法规标题、机关、文号、发布日期、生效日期、页数、条款数和待确认字段；缺失文号不会用模型常识补齐。
- S2 适用性判断：支持机构类型、业务范围、地域和解读时点输入；输出 `DIRECTLY_APPLICABLE` 或 `NEEDS_REVIEW`、匹配阶段、理由和证据要求。
- S3 监管要求抽取：按条款保存 Requirement，保留主体、行为、对象、条件、例外、频率、时限、阈值、数字表达和原文片段；规则类型固定为 `OBLIGATION`、`PROHIBITION`、`PERMISSION`、`SCOPE`、`OTHER` 等。
- S4 解读：生成整体解读和逐条解读，每条包含 `FACT`、`OFFICIAL`、`INTERPRETATION` 内容块，绑定 Article/Evidence，状态统一为 `needs_review`，不直接宣称正式结论。
- API：`POST /api/tasks/{task_id}/interpret`、`GET /api/tasks/{task_id}/interpretation`、`GET /api/tasks/{task_id}/requirements`。
- 数据库：新增 S1—S4 输出元数据迁移 `backend/migrations/versions/cf7a0d6a10f2_add_pipeline_output_metadata.py`。
- 前端：工作台新增“运行 S1—S4”入口、流水线状态、适用性判断、结构化监管要求和逐条解读展示；未连接 API 时明确提示，不伪造成功。
- 当前边界：默认使用规则生成模式；模型 Provider 仍通过环境变量保留可替换接口，QC、人工锁定、异步重跑和正式发布闸门不在第十步内完成。

## 第 11 步当前交付

- 复核 API：`backend/app/api/review.py`，包括复核结果读取、法规元数据修订、Requirement 逐项复核、Interpretation 编辑/锁定、证据核验、QC 和 DOCX 导出/下载。
- 复核服务：`backend/app/services/review.py`，检查原文片段、Article/Evidence 绑定、待确认元数据、附件缺失、逐项复核锁定、证据核验和 S5 跳过边界。
- 导出服务：`backend/app/services/docx_export.py`，生成法规概览、适用性判断、监管要求、逐条解读、证据链和真实性边界说明；报告只有在 `ready_for_export` 后生成。
- 状态流转：`waiting_review → reviewing → ready_for_export → exported`；QC 存在阻断项时保持 `reviewing`，不允许导出。
- 前端：`src/App.jsx` 新增“人工复核与交付闸门”面板，支持元数据、Requirement、整体/逐条解读和证据核验；公开 Pages 未连接 API 时不伪造复核或导出。
- 依赖：后端新增 `python-docx`，用于基础 Word 交付物生成。
- 测试：`tests/backend/test_review_api.py` 覆盖复核留痕、证据保护、QC 阻断、QC 通过和 DOCX 下载；本地隔离环境全量测试 `15 passed`，前端生产构建通过。
- DOCX 视觉检查：已通过 LibreOffice 转 PDF、PNG 渲染复核；修正了中文字体映射和渲染环境字体配置后，2 页测试报告可读，无方框文字或明显溢出。
- 真实法规核验：已用项目内 2017 年 PDF 在私有模式 SQLite 后端执行导入和 S1—S4；成功识别 25 条，QC 按设计阻断，阻断码包括 `UNRESOLVED_METADATA`、`MISSING_ATTACHMENT_SOURCE`、`EVIDENCE_NOT_VERIFIED`、`REQUIREMENT_NOT_REVIEWED` 和 `INTERPRETATION_NOT_LOCKED`。
- 未完成：真实 2017 年 PDF 尚未完成“将用户确认的文号写入任务元数据/附件边界确认 → 全量复核 → QC 通过 → 实际导出”的闭环；不能把本次阻断结果标记为可交付。

## 用户确认开发顺序：第 4 项交付（S1 元数据识别与人工修订闭环）

- S1 字段状态：标题、文号、发布机关、发布日期和生效日期均输出 `value`、机器值、状态、置信度、提取方式、来源文件编号和来源页码。
- 真实性边界：机器从 OCR 页面识别出的字段标记为 `needs_review`；未识别字段标记为 `missing`；不会把 OCR 候选值直接当成已核验事实。
- 人工修订：复核面板新增发布日期、生效日期和元数据字段状态卡；人工保存后记录 `manual_verified`、复核人、复核时间和机器原值，并写入审计日志。
- 重跑保护：重新运行 S1—S4 时保留人工覆盖值和状态；同时修复流水线重跑时监管要求 ID 冲突问题，使每次运行拥有独立的要求记录。
- 验证结果：S1 元数据闭环回归测试通过；全量后端测试 `19 passed`；Python 编译通过；前端生产构建通过；`git diff --check` 通过。

## 用户确认开发顺序：第 5 项交付（S2 法规定位、适用范围与版本关系）

- 法规定位：S2 输出法规、版本、来源文件、文件名、SHA-256、页数、解析状态、来源警告和待确认字段，明确定位依据来自已登记来源文件和法规版本。
- 适用性判断：支持 `DIRECTLY_APPLICABLE`、`POTENTIALLY_APPLICABLE`、`NOT_APPLICABLE`、`NEEDS_REVIEW` 四种结果，分别考虑机构类型、业务范围、地域边界和解读时点。
- 证据定位：适用性结论附带 Article、页码、匹配关键词和原文片段；找不到直接支持片段时显示待人工复核。
- 版本关系：识别数据库已登记的前一版本，也识别正文中提及的旧文号、旧版本和“废止/替代/修订”线索；只有前版本已登记时才标记为已识别，否则保持 `CANDIDATE_NEEDS_VERIFICATION`，不启动 S5 差异结论。
- 前端：概览页新增法规定位、适用性依据、版本关系和四类适用性状态展示。
- 验证结果：全量后端测试 `21 passed`；真实 2017 年 PDF 解析 25 条，识别第二十五条提及的 `财金〔2015〕60号` 为待核验前版线索；前端生产构建、Python 编译和 `git diff --check` 通过。

## 用户确认开发顺序：第 6 项交付（S3 条款拆解、监管规则抽取与数字识别）

- 原子化拆解：同一条款中包含多个独立动作时拆分为多个 Requirement；保留 Article 原文、条款号、页码、行号和来源文件哈希，不改写监管原文。
- 规则字段：补充规范词、动作强度（`must`、`should`、`must_not`、`prohibited`、`permission`）、动作类别、条件、例外、交叉引用、频率类别和过渡期字段。
- 数字识别：数字输出原始表达、数字类型、规范化值、字符起止位置和上下文；支持期限、日期、金额、比例、附件引用和文号，并排除“2015年修订版”等版本标签误识别。
- 真实法规结果：2017 年 PDF 的 25 条正文识别出 56 个原子监管要求；准确保留 `2年内`、`5个月内`、`6个月内`、`2017年10月1日起`、`财金〔2015〕60号` 以及 `附1/附2/附3` 引用。
- 前端：核心要求页新增原子要求数量、数字表达数量、规范词数量、复核提示、行为强度和数字/时限展示。
- 验证结果：全量后端测试 `23 passed`；真实法规解析验证通过；前端生产构建、Python 编译和 `git diff --check` 通过。

## 用户确认开发顺序：第 7 项交付（S5 新旧规比较）

- 比较服务：新增 `backend/app/services/version_compare.py`，在旧规原文、两份文件哈希和版本关系均满足条件后，按条款号识别 `ADDED`、`DELETED`、`MODIFIED`，并输出文本差异、数字变化、适用范围、时间、阈值和规范强度等变化维度。
- 证据链：每条变化分别保留旧规/新规的版本编号、来源文件编号、文件哈希、页码、原文条款号、行号定位和原文片段；S5 不把变化自动扩展成制度、整改或法律意见。
- 质量闸门：没有旧规时返回 `SKIPPED_NO_PREVIOUS_SOURCE`；前一版本存在但关系未确认时返回 `WAITING_RELATION_CONFIRMATION`；原文、哈希或条款结构不完整时返回 `WAITING_SOURCE_VERIFICATION`；这些状态均不生成差异行。
- API：新增 `POST /api/tasks/{task_id}/s5/confirm-relation` 和 `POST /api/tasks/{task_id}/s5/compare`；有权限的机构成员可确认版本关系并从页面触发比较，写入 `VersionRelation` 和审计日志。
- 前端：版本比较页已消费真实 S5 输出；当前 CASE-001 继续显示“待补充权威原文”，有两份核验版本时显示新增/删除/修改统计和新旧原文证据卡。
- QC：S5 `blocked` 会阻断发布，S5 `skipped` 作为明确的待补充边界提示；不会因缺少旧规而伪造变化结论。
- 验证结果：S5 专项测试 3 项通过；全量后端测试 `26 passed`；前端生产构建通过；Python 编译和 `git diff --check` 通过。
- 当前真实状态：CASE-001 仍没有可核验的 2015 年版原文，因此 S5 真实运行结果是跳过而非比较完成。要看到真实差异，下一步需上传旧规全文并由有权限人员确认版本关系。

## 用户确认开发顺序：第 8 项交付（S4 整体解读、逐条解读与变化解读）

- S4 生成服务：新增 `backend/app/services/interpretation_s4.py`，将整体解读、逐条解读和 S5 变化解读拆为可测试的证据优先生成逻辑。
- 整体解读：输出法规概览、登记的发布/生效信息、适用性判断、S3要求统计、关键要求和当前S5状态；FACT、OFFICIAL、INTERPRETATION、CHANGE 内容块分开保存。
- 逐条解读：基于每条 Article 和对应 Requirement 生成主体、动作、对象、条件、例外、期限等说明，保留 Article/Evidence 绑定并统一标记为待人工复核。
- 变化解读：只有 S5 为 `COMPLETED` 时，才为对应条款生成 CHANGE 内容块；内容仅复述可定位的新增、删除、修改和变化维度，不自动判断趋严、放宽、企业影响或整改要求。
- 缺口边界：S5 为 `SKIPPED_NO_PREVIOUS_SOURCE`、`WAITING_RELATION_CONFIRMATION` 或 `WAITING_SOURCE_VERIFICATION` 时，S4明确输出“未生成变化解读”，不使用行业常识补齐。
- 前端：条款解读页展示整体变化解读状态和 CHANGE 内容块；当前 CASE-001 页面仍显示旧规缺失边界。
- 验证结果：新增 S4 专项测试；全量后端测试 `28 passed`；前端生产构建、Python 编译和 `git diff --check` 通过。

## 用户确认开发顺序：第 9 项交付（Evidence 链路、Content Package 与人工锁定版本）

- 证据链校验：新增 `backend/app/services/evidence_service.py`，统一检查 `Interpretation → Requirement → Article → Evidence → SourceDocument` 绑定、证据引用存在性、页码、原文片段和文件哈希。
- 内容包服务：新增 `backend/app/services/content_package_service.py`，生成 HTML 和 Word 共用的 `content-package-v1`，包含法规元数据、整体解读、逐条解读、监管要求、文章导航、证据链接、S5结果和来源哈希。
- 内容包持久化：新增 `content_packages` 表和 `POST/GET /api/tasks/{task_id}/content-package`；内容包带版本号、SHA-256、流水线运行号和锁定人。旧包不会被覆盖，新包生成时旧包标记为 `SUPERSEDED`。
- 人工锁定版本：新增 `content_versions` 表；每次保存 Interpretation 都保存前后状态快照和内容哈希，人工复核并锁定的版本标记为 `HUMAN_LOCKED`。锁定内容再次修改前必须显式解除锁定。
- 失效保护：上游元数据、Requirement、Interpretation 或 Evidence 发生变化时，已有锁定 Content Package 标记为 `STALE`，避免继续误用旧内容包。
- 前端：人工复核面板新增“生成锁定内容包”入口；未满足解读锁定、Requirement 复核和证据核验条件时，页面显示阻断原因。
- 数据库迁移：新增 `backend/migrations/versions/d4e8b6a1c902_add_content_packages_and_versions.py`，已验证 Alembic upgrade head 和 downgrade base。
- 验证结果：全量后端测试 `29 passed`；Content Package 端到端证据链测试通过；前端生产构建、Python 编译、Alembic 升降级和 `git diff --check` 通过。
- 当前边界：Content Package 已能生成并作为统一数据契约使用；HTML/Word Renderer 仍在后续第 13 项继续改为只消费锁定内容包。

## 用户确认开发顺序：第 10 项交付（规则 QC、LLM Reviewer、人工审核退回与发布闸门）

- 规则 QC：新增 `backend/app/services/qc_rules.py`，检查监管要求原文是否仍可回定位、数字表达是否进入结构化字段、内容块标签和证据是否完整、解读是否出现绝对化表述，以及证据来源哈希是否一致。规则发现会以阻断项写入 `QCResult`，不会静默放行。
- LLM Reviewer：新增 `backend/app/services/llm_reviewer.py` 和 `POST /api/tasks/{task_id}/review/llm`。支持 OpenAI-compatible Chat Completions JSON 适配；未配置 Provider、模型或 API Key 时明确返回 `not_configured`，不把规则生成结果冒充模型复核。通过 `LLM_REVIEWER_REQUIRED=true` 或任务级配置可将未运行/未配置变为发布阻断。
- 人工审核：保留“修改前显式解除锁定、保存内容版本、保留证据绑定、写入审计日志”的约束；新增 `POST /api/tasks/{task_id}/review/decision`，支持 `return` 退回修改、`approve` 审核批准和 `publish` 正式发布。
- 退回逻辑：整任务退回时将 Interpretation 解锁并置为 `needs_review`、Requirement 置为 `needs_review`，已有 Content Package 标记 `STALE`；指定单个目标时只退回目标对象。修改后必须重新运行 QC。
- 发布闸门：必须满足最新 QC 为 `passed`、Content Package 状态为 `HUMAN_LOCKED`，才允许任务进入 `published`；没有锁定内容包、QC 过期或存在阻断项均返回 409。
- 前端：人工复核面板新增“运行 LLM Reviewer”“退回修改”和“发布”按钮，并明确展示模型未配置/需要处理状态；公开 Pages 未连接后端时仍不会伪造审核和发布成功。
- 配置：`.env.example` 和 Compose 增加 `LLM_REVIEWER_REQUIRED`；默认关闭强制模型复核，原因是当前环境尚未提供真实模型 API Key。
- 验证结果：全量后端测试 `30 passed`；前端生产构建通过；Python 编译和 `git diff --check` 通过。回归覆盖规则 QC、LLM 未配置显式状态、退回修改、QC 通过后生成 Content Package 并发布。
- 当前真实边界：模型 Provider 尚未在当前环境配置，因此 LLM Reviewer 只能验证“未配置不冒充通过”的安全行为；要获得真实模型审阅结果，需要在私有部署环境配置真实 Provider、模型和 API Key。

## 用户确认开发顺序：第 11 项交付（Workflow、异步任务、进度、失败恢复与节点重跑）

- 持久化模型：新增 `workflow_runs` 和 `workflow_nodes` 表，保存工作流状态、当前节点、进度、尝试次数、错误信息、Celery 任务号和每个节点的检查点。
- 工作流节点：当前解释工作流按 `S1 → S2 → S3 → S4 → S5` 编排；S5 没有可核验旧规时记录为 `skipped`，不会伪造比较结果。
- 异步执行：新增 Celery 任务 `workflow.execute`；Docker Compose 的 Worker 现在能够加载后端代码、共享数据卷并消费 Redis 队列。开发/测试可用 `WORKFLOW_EXECUTION_MODE=inline`，准生产默认使用 `celery`。
- API：新增 `POST /api/tasks/{task_id}/workflow`、`GET /api/tasks/{task_id}/workflow`、`GET /api/workflows/{workflow_id}`、`POST /api/workflows/{workflow_id}/retry` 和 `POST /api/workflows/{workflow_id}/rerun`。
- 进度：前端从启动工作流改为轮询工作流状态，显示总体百分比、当前节点、节点状态和失败原因；失败节点可重跑，失败工作流可重试。
- 一致性保护：请求重跑任一节点时会记录 `requested_from` 和父工作流；为避免 S1—S5 之间产生不一致，当前实现从请求节点重新计算完整解释流水线，并在工作流中保留该重跑来源。
- 失败恢复：失败状态保留节点、错误码、错误消息和是否可重试；重试次数默认最多 2 次，超过上限后不再自动放行。
- 数据库迁移：新增 `backend/migrations/versions/8f4a2c6e1b77_add_workflow_runs_and_nodes.py`，已验证 Alembic upgrade head 和 downgrade base。
- 验证结果：全量后端测试 `31 passed`；Workflow 失败、重试、节点重跑专项测试通过；前端生产构建通过；Worker Celery 任务注册、Python 编译和 `git diff --check` 通过。
- 当前边界：当前 API 仍保留旧的同步 `POST /api/tasks/{task_id}/interpret` 兼容接口；前端运行入口已切换到 Workflow。要在真实环境执行异步任务，还需要部署并启动 PostgreSQL、Redis 和 Worker，这属于后续准生产部署项。

## 用户确认开发顺序：第 12 项交付（首页、任务页、Workflow、解读、条款、比较、审核和报告中心）

- 页面导航：左侧任务/目录栏新增工作台页面导航，支持首页、当前任务、Workflow、解读总览、条款解读、版本比较、人工审核和报告中心；三栏工作台结构保持不变。
- 首页：展示当前法规任务、Workflow 进度、结构化要求数量、当前发布边界和主要操作入口；未连接后端时明确显示“前端预览”。
- 任务页：保留原有法规概览、核心要求、条款解读、版本比较四个工作标签，并接入第 11 项 Workflow 入口。
- Workflow 页：展示 S1—S5 节点说明、当前进度、检查点、失败原因、重试和节点重跑入口。
- 解读总览页：集中展示 S1/S2/S3/S4 结果和适用性、来源边界、监管要求统计。
- 条款解读页：展示逐条 Requirement、Interpretation 内容块和 Evidence 定位；无真实后端结果时保持待运行状态。
- 比较页：复用 S5 真实比较结果和“旧规缺失/关系待核验/来源待核验”边界，不生成虚假差异。
- 审核页：展示人工复核、证据核验、Content Package 和发布闸门说明，并可打开完整审核工作台。
- 报告中心：展示报告组成、导出状态和 HTML/Word 共用 Content Package 的一致性约束。
- 视觉实现：沿用 Swiss 视觉方向，使用白底、细网格、左对齐信息层级和 Deloitte 绿色强调色；新增页面不改变顶部栏、左侧任务/目录、中间内容、右侧证据链布局。
- 验证结果：后端测试 `31 passed`；前端生产构建通过；Python 编译和 `git diff --check` 通过。
- 当前边界：公开 Pages/本地前端预览仍不会凭空显示真实后端数据；要看到 Workflow 实时状态和审核结果，必须配置 `VITE_API_BASE_URL` 并启动 API、PostgreSQL、Redis 和 Worker。

## 用户确认开发顺序：第 13 项交付（HTML Renderer、Word Renderer、下载与一致性检查）

- 统一输入：新增 `backend/app/services/report_renderer.py`；HTML 和 Word 均只消费 `HUMAN_LOCKED` Content Package，不再从可变的人工复核对象重新拼装报告。
- HTML Renderer：生成可独立打开的法规报告 HTML，包含法规概览、整体解读、监管要求、逐条原文/解读、S5 状态和 Evidence 链路；页面内记录 Content Package 编号和 SHA-256。
- Word Renderer：生成与 HTML 共享内容哈希的 `.docx` 交付物，保留法规原文、结构化要求、逐条解读、版本比较边界和证据定位。
- 导出 API：`POST /api/tasks/{task_id}/export/docx` 现在同时生成 HTML 和 Word；若尚无锁定 Content Package，会在满足全部人工锁定、Requirement 复核、Evidence 核验和 QC 条件时自动创建，否则返回阻断原因。
- 下载 API：保留 Word 下载地址，并新增 `/api/tasks/{task_id}/exports/{report_id}/html`；报告中心显示两个下载入口、Package 版本/哈希和一致性状态。
- 一致性检查：逐项核验两种格式是否包含同一 Content Package 的关键法规元数据、条款、Requirement、Evidence 和内容哈希；检查未通过时不提交导出状态。
- 验证结果：全量后端测试 `31 passed`；HTML/Word 下载和哈希一致性已纳入回归测试；前端生产构建、Python 编译和 `git diff --check` 通过。DOCX 已按文档技能要求完成渲染检查；当前无 CJK 字体的 headless LibreOffice 环境会把中文显示为缺字框，代码已使用 macOS 可用的 `Hiragino Sans GB`，实际 Mac Word/已安装中文字体环境需再做最终视觉验收。
- 当前边界：交付物渲染和下载链路已完成，但真实公网 API、PostgreSQL、Redis、Worker、模型 API 和生产监控仍需在第 16 项准生产部署中完成；当前环境未配置真实模型时，报告不会声称获得模型复核。

## 用户确认开发顺序：第 14 项交付（Benchmark、端到端、权限、安全与回归测试）

- Benchmark 清单：新增 `benchmarks/manifest.json`，覆盖 6 个案例、3 类机构（BANK、CONSUMER_FINANCE、FINANCE_COMPANY）、6 种版式标签（官方网页打印 PDF、单栏、双栏、扫描、附件型、OCR 噪声）和 4 类风险（资产质量、信用、操作、市场）。
- Benchmark 资产：新增 5 个可读文本夹具，清单为每个案例冻结条款数、S5 安全状态和可重放断言；CASE-001 继续使用真实 2017 年法规 PDF 和 Gold 文件。
- Benchmark Runner：新增 `python -m benchmarks.runner`，校验案例唯一性、机构/版式/风险覆盖、源文件与 Gold 资产、条款数和 S5 边界；当前报告为 6 cases / 20 assertions / 0 asset errors。
- 端到端测试：新增 Workflow → 人工复核 → QC → Content Package → HTML/Word 下载的完整验收测试，确认交付物内容哈希一致。
- 权限测试：新增跨机构法规读取、法规列表隔离、跨机构任务引用阻断和来源文件目录穿越阻断测试。
- 安全修复：法规现在绑定机构空间；法规读取、列表、任务引用、文章读取和来源文件下载均执行机构隔离；手工登记 SourceDocument 时拒绝绝对路径和 `..` 路径片段。
- 数据库迁移：新增 `backend/migrations/versions/3a7c2d1e9f44_scope_regulations_to_organizations.py`，同时合并原有两个 Alembic head；已完成 SQLite 临时库 `upgrade head` 和 `downgrade base`。
- 验证结果：全量后端回归测试 `35 passed`；Benchmark Runner 通过；前端生产构建、Python 编译和 `git diff --check` 通过。
- 当前边界：Benchmark 已完成自动结构校验和主流程回归，但多机构真实业务样本、真实扫描 PDF/OCR 样本和真实审阅人员 Gold 复核仍需在准生产部署后补齐；正式公网环境尚未部署。
