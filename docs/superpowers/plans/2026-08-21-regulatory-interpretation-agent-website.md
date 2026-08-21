# 真实可用外规解读 Agent 网站实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建设一个名为“外规解读智能体工作台”的真实可用网站，面向银行、保险、证券、基金、期货、信托、金融租赁、支付、消费金融、财务公司和小额贷款机构，实现“选择机构类型 → 上传法规 → 条款解析 → 外规解读 → 证据追踪 → HTML 阅读 → Word 导出”的完整闭环。

**Architecture:** 采用前后端分离的可部署架构。前端负责任务创建、过程状态和结果阅读；后端负责文件、任务、数据和权限；后台 Worker 负责文档解析、S1–S4、证据绑定和 QC。原始法规文本不可变，所有 AI 结果必须带版本、来源和证据定位。

**Tech Stack:** 默认使用 Next.js + TypeScript 前端、FastAPI + Python 后端、PostgreSQL、Redis 队列、S3 兼容文件存储、Docker Compose；模型通过可替换的 OpenAI-compatible Provider Adapter 调用，所有密钥仅通过环境变量注入。

**Spec:** `外规解读 Agent Handoff Document v1.0.md`、`外规解读 Agent v2.0 开发规格.md`、`外规解读 Agent Data Schema v1.0.md`、`外规解读 Agent API Specification v1.0.md`、`外规解读 Agent MVP开发计划与实施路线图 v1.0.md`。

## Global Constraints

- 产品范围只包含外规解析、结构化、条款拆解、外规解读、证据绑定、HTML 阅读和 Word 报告。
- 不实现外规内化、制度映射、制度 Gap、流程优化、内控评价、审计测试或整改闭环。
- 适用性结论必须区分“直接适用、潜在适用、不适用、待确认”，不得把模型推断写成监管原文。
- 事实、官方解释和 Agent 解读分别标记为 `FACT`、`OFFICIAL`、`INTERPRETATION`。
- `Article.original_text` 只读；人工修改产生新版本，不覆盖原始文本或已锁定内容。
- 每一条核心结论必须能回溯到 `Requirement → Article → SourceDocument → source_location`。
- S5 新旧规比较属于网站能力；当用户提供两份已核验且版本关系明确的法规时必须启用。缺少旧规或版本关系不明时显示“待补充/待确认”，不得强行比较。
- 任何法规事实错误、关键限定条件遗漏、数字错误、证据缺失或导航断链都不得发布。

---

## 一、先冻结目标和验收口径

### Task 1：冻结第一版产品范围

**Files:**
- Create: `docs/PRODUCT_SCOPE.md`
- Modify: `外规解读 Agent PRD v1.0.md`（如需同步，不改变已确认边界）

**工作内容：**

- 明确首页必须支持的机构类型：银行、保险、证券、基金、期货、信托、金融租赁、支付、消费金融、财务公司、小额贷款。
- 明确第一版不做制度映射、Gap、审计和整改。
- 明确第一版输入为 PDF，后续再扩展 DOCX、扫描件批量上传。
- 明确第一版输出为结构化结果、HTML 阅读页和 DOCX 报告。
- 明确机构类型只用于适用性判断和解读上下文，不改变监管原文。

**完成标准：**

- 任意开发任务都能判断是否属于第一版范围。
- 产品首页、任务页、结果页的范围没有相互矛盾。

### Task 2：建立端到端验收案例

**Files:**
- Create: `benchmarks/cases/case-001-bad-debt-writeoff.yaml`
- Create: `benchmarks/gold/case-001.json`
- Create: `docs/ACCEPTANCE_CRITERIA.md`

**工作内容：**

- 以《金融企业呆账核销管理办法》作为第一条完整验收法规。
- 为案例记录机构类型、监管地域、任务目标、期望识别的元数据、重点条款、数字字段、适用性结论和证据位置。
- 至少标注 10 个高风险事实点：日期、文号、适用对象、应/不得/可以、条件、例外、比例、时限、责任主体和条款引用。
- 设定发布门槛：关键事实正确、证据可定位、HTML 与 Word 内容一致、失败任务可恢复。

**完成标准：**

- 有人工确认的 Gold JSON。
- 后续 S1–S4、QC、渲染和端到端测试都使用同一案例验收。

---

## 二、搭建实际工程基础

### Task 3：建立代码仓库和运行骨架

**Files:**
- Create: `frontend/`
- Create: `backend/`
- Create: `worker/`
- Create: `tests/`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `Makefile`
- Create: `README.md`

**工作内容：**

- 建立前端、后端、Worker、测试和基础设施目录。
- 提供 `web`、`api`、`worker`、`postgres`、`redis`、`minio` 的本地启动配置。
- 增加 `/health`、`/ready` 和 Worker 心跳检查。
- 配置 TypeScript、Python lint、格式化和单元测试命令。
- `.env.example` 只包含变量名和说明，不写入真实密钥。

**完成标准：**

- 新环境执行一条命令可以启动基础服务。
- 前端可以打开，后端健康检查通过，Worker 可以消费测试任务。

### Task 4：冻结工程决策和配置边界

**Files:**
- Create: `docs/ARCHITECTURE_DECISIONS.md`
- Create: `backend/app/core/config.py`
- Create: `worker/app/core/config.py`
- Create: `frontend/src/lib/config.ts`

**工作内容：**

- 固定数据库、队列、文件存储、模型 Provider、日志和部署配置。
- 设计 `LLMProvider` 接口，至少支持模型名称、超时、重试、JSON 输出和调用审计。
- 设计 `StorageProvider` 接口，支持本地 MinIO 和生产 S3 兼容存储。
- 设计同步短任务与异步长任务边界：上传、查询可同步；解析、解读、报告生成必须异步。

**完成标准：**

- 更换模型 Provider 不需要修改 S1–S4 业务逻辑。
- 开发环境、测试环境和生产环境的配置来源明确。

---

## 三、建立可追溯的数据底座

### Task 5：实现数据库 Schema 和迁移

**Files:**
- Create: `backend/migrations/`
- Create: `backend/app/models/task.py`
- Create: `backend/app/models/source_document.py`
- Create: `backend/app/models/regulation.py`
- Create: `backend/app/models/article.py`
- Create: `backend/app/models/requirement.py`
- Create: `backend/app/models/interpretation.py`
- Create: `backend/app/models/evidence.py`
- Create: `backend/app/models/qc_result.py`
- Create: `backend/app/models/report.py`
- Test: `tests/backend/test_schema_integrity.py`

**工作内容：**

- 建立 Task、SourceDocument、Regulation、Article、Requirement、Interpretation、Evidence、QCResult、Report、ReviewEvent 和 PromptVersion。
- 所有业务对象使用稳定 ID；法规版本、Prompt 版本、内容版本单独保存。
- 保存文件哈希、原始文件位置、解析版本、页码、段落和字符区间。
- 为 Article 原文设置不可变约束或应用层拒绝覆盖。
- 为 Evidence 建立双向引用，支持从结论跳到原文，也支持从条款查看被哪些结论引用。

**完成标准：**

- 数据库可以保存完整的 S1–S4 结果。
- 删除或修改原始法规时有明确拒绝或审计记录。
- 数据库测试覆盖唯一性、外键、版本和证据链完整性。

### Task 6：实现任务状态和断点恢复

**Files:**
- Create: `backend/app/services/task_service.py`
- Create: `worker/app/workflow/state_machine.py`
- Test: `tests/backend/test_task_state_machine.py`

**工作内容：**

- 固定状态：`DRAFT`、`UPLOADED`、`PARSING`、`IDENTIFYING`、`EXTRACTING`、`INTERPRETING`、`QC_PENDING`、`READY`、`FAILED`、`CANCELLED`。
- 每个节点保存开始时间、结束时间、输入版本、输出版本、错误码和重试次数。
- 支持从失败节点重跑，不重复覆盖已锁定结果。
- 为不可恢复错误给出用户可理解的失败原因。

**完成标准：**

- Worker 中断后任务可以从最近成功节点继续。
- 同一节点重复执行不会产生无法追踪的重复结果。

---

## 四、实现文件上传和法规解析

### Task 7：实现上传、校验和文件存储

**Files:**
- Create: `backend/app/api/documents.py`
- Create: `backend/app/services/document_service.py`
- Create: `backend/app/storage/object_storage.py`
- Create: `frontend/src/app/tasks/new/page.tsx`
- Test: `tests/backend/test_document_upload.py`

**工作内容：**

- 支持 PDF 上传，限制文件大小、扩展名和 MIME 类型。
- 对文件生成 SHA-256 哈希，保存原始文件，不以解析结果替代原文件。
- 拒绝空文件、损坏 PDF、超限文件和不支持格式，并在页面显示原因。
- 支持重复文件检测；重复文件可以引用已有源文件，但任务仍有独立记录。
- 上传完成后自动创建 Task 和 SourceDocument。

**完成标准：**

- 用户可以从网页上传一份法规并看到任务进入 `UPLOADED`。
- 原始文件可下载或受权限保护地预览。

### Task 8：实现文本提取、页码和 OCR 兜底

**Files:**
- Create: `worker/app/parsing/pdf_parser.py`
- Create: `worker/app/parsing/ocr_fallback.py`
- Create: `worker/app/parsing/structure_detector.py`
- Test: `tests/worker/test_pdf_parser.py`
- Test: `tests/worker/fixtures/`

**工作内容：**

- 优先提取 PDF 原生文本，保存页码、段落顺序和字符位置。
- 对扫描型 PDF 触发 OCR，并标记 `ocr_used=true` 和 OCR 置信度。
- 识别法规标题、文号、发文机关、发布日期、施行日期、章节和条款编号。
- 保留原始页图或页级引用，确保 HTML 和 Word 可以跳回原文位置。
- 解析失败时任务进入 `FAILED`，不能生成伪造解读。

**完成标准：**

- Case 001 的条款顺序、页码和原文与人工标准一致。
- OCR 不清晰的字段被标记为待确认，而不是自动补全。

---

## 五、实现不同金融机构类型的外规识别

### Task 9：建立机构类型和适用性配置

**Files:**
- Create: `backend/app/domain/institution_types.py`
- Create: `backend/app/domain/applicability_rules.py`
- Create: `backend/app/api/applicability.py`
- Create: `frontend/src/components/InstitutionTypeSelector.tsx`
- Create: `frontend/src/components/ApplicabilityPanel.tsx`
- Create: `benchmarks/institution-types.yaml`
- Test: `tests/backend/test_applicability.py`

**工作内容：**

- 建立机构类型枚举和展示名称，不把类型名称直接写死在 Prompt 中。
- 任务创建时记录机构类型、业务范围、地域和解读时点。
- S2 输出适用性状态：`DIRECTLY_APPLICABLE`、`POTENTIALLY_APPLICABLE`、`NOT_APPLICABLE`、`NEEDS_REVIEW`。
- 每个适用性结论必须包含依据条款、官方来源或待人工确认原因。
- 对无法判断的法规，不向用户承诺“适用”或“不适用”。

**完成标准：**

- 用户可以选择不同金融机构类型创建任务。
- 同一法规在不同机构类型下能显示不同的适用性结论，但原文和条款不被改变。
- 适用性判断页面能明确显示证据和不确定性。

### Task 10：实现 S1 法规元数据识别

**Files:**
- Create: `worker/app/skills/s1_document_parser.py`
- Create: `worker/app/prompts/s1_document_parser.md`
- Create: `backend/app/schemas/regulation.py`
- Test: `tests/worker/test_s1_document_parser.py`

**工作内容：**

- 从解析文本中生成 Regulation Object。
- 提取法规名称、发文机关、文号、发布日期、施行日期、废止/修订信息和条款范围。
- 对不确定字段返回候选值、证据位置和置信度。
- 所有模型输出先经过 JSON Schema 校验，再写入数据库。

**完成标准：**

- Case 001 的元数据全部可定位。
- 缺失字段显示“待确认”，不使用模型常识填补。

### Task 11：实现 S2 法规关系与适用范围识别

**Files:**
- Create: `worker/app/skills/s2_regulation_identifier.py`
- Create: `worker/app/prompts/s2_regulation_identifier.md`
- Test: `tests/worker/test_s2_regulation_identifier.py`

**工作内容：**

- 根据机构类型、业务范围、地域和时点识别适用范围。
- 区分法规原文明确范围、官方说明和模型初步判断。
- 版本关系只有在输入材料有明确依据时才记录；没有依据则标记待确认。
- 输出监管分类、适用性、关联法规候选和证据。

**完成标准：**

- 机构类型、适用性状态和证据可以在前端展示。
- 不会将“金融机构”自动等同为所有金融机构均直接适用。

### Task 12：实现 S3 条款拆解和监管规则抽取

**Files:**
- Create: `worker/app/skills/s3_requirement_extractor.py`
- Create: `worker/app/prompts/s3_requirement_extractor.md`
- Create: `backend/app/schemas/requirement.py`
- Test: `tests/worker/test_s3_requirement_extractor.py`

**工作内容：**

- 按“一条监管要求一个 Requirement”拆解条款。
- 提取主体、动作、对象、条件、例外、频率、时限、数字、责任、审批和报送要求。
- 特别处理“应、应当、不得、可以、原则上、至少、不超过、除……外”等法律措辞。
- 保留 Article、段落和原文字符位置；复合义务拆分后保留共同上下文。
- 输出置信度、待人工确认项和原文证据。

**完成标准：**

- Case 001 的高风险事实点全部结构化。
- 数字、否定词、限定条件和例外没有丢失。
- 每个 Requirement 都能反查 Article。

### Task 12A：实现 S5 新旧规比较

**Files:**
- Create: `worker/app/skills/s5_version_compare.py`
- Create: `worker/app/prompts/s5_version_compare.md`
- Create: `backend/app/schemas/version_relation.py`
- Create: `backend/app/schemas/change.py`
- Create: `frontend/src/components/VersionComparePanel.tsx`
- Test: `tests/worker/test_s5_version_compare.py`

**工作内容：**

- 支持用户上传新规和旧规，或从法规库选择两份已核验版本。
- 记录版本关系：直接前序版本、历史版本、关联法规或待确认。
- 在两份法规分别完成 S1–S3 后进行条款映射和文本比较。
- 识别新增、删除、修订、范围变化、时间变化、金额变化、比例变化和阈值变化。
- 先输出文本事实变化，再输出谨慎的监管含义解释；没有证据时不判断收紧或放宽。
- 对缺少旧规、版本关系不明、条款无法映射的情况输出明确阻断原因。

**完成标准：**

- 用户可以查看旧规、新规、变化类型、差异文本和证据。
- 错误版本关系不能进入正式比较结果。
- 只有在两份法规和版本关系均通过 QC 后，比较结果才能发布。

---

## 六、实现外规解读和证据链

### Task 13：实现 S4 整体解读和逐条解读

**Files:**
- Create: `worker/app/skills/s4_interpreter.py`
- Create: `worker/app/prompts/s4_overview.md`
- Create: `worker/app/prompts/s4_article_interpreter.md`
- Create: `backend/app/schemas/interpretation.py`
- Test: `tests/worker/test_s4_interpreter.py`

**工作内容：**

- 整体解读输出背景、目的、法规定位、适用范围、核心要求和监管框架。
- 逐条解读固定输出：原文、外规解读、核心要求、关联条款、证据来源。
- 在存在 S5 结果时，补充变化解读；没有已核验旧规时不生成变化结论。
- 强制区分 `FACT`、`OFFICIAL`、`INTERPRETATION`。
- 禁止新增原文不存在的义务，禁止绝对化和夸大表达。
- 解读必须只基于已确认的 Regulation、Article、Requirement 和 Evidence。
- 输出人工锁定状态和 Prompt 版本。

**完成标准：**

- Case 001 能生成整体解读和逐条解读。
- 每条解读至少有一个可定位证据；没有证据的内容进入待审核，不得直接发布。

### Task 14：实现 Evidence 服务和内容包

**Files:**
- Create: `backend/app/services/evidence_service.py`
- Create: `backend/app/services/content_package_service.py`
- Create: `backend/app/schemas/evidence.py`
- Test: `tests/backend/test_evidence_chain.py`

**工作内容：**

- 建立 `Conclusion → Interpretation → Requirement → Article → SourceDocument` 链路。
- 证据保存来源等级、文件哈希、页码、段落、字符位置和引用文本。
- 生成给前端和 Word Renderer 共用的 Content Package。
- 内容包生成后带版本号和 QC 状态；前端不得自行拼接业务内容。

**完成标准：**

- 点击任一结论可以定位到条款和原文页码。
- 上游内容变更会生成新版本，不覆盖已审核版本。

---

## 七、实现 QC 和人工审核

### Task 15：实现规则型 QC

**Files:**
- Create: `worker/app/qc/rule_checks.py`
- Create: `worker/app/qc/source_checks.py`
- Create: `worker/app/qc/number_checks.py`
- Create: `worker/app/qc/evidence_checks.py`
- Test: `tests/worker/test_qc_rules.py`

**工作内容：**

- 检查原文是否存在、条款是否完整、顺序是否正确。
- 对日期、金额、比例、时间、数字做原文与输出比对。
- 检查所有核心解读是否绑定证据。
- 检查 Article、Requirement、Interpretation 的引用关系和版本一致性。
- 发现 BLOCKER 时阻止发布。

**完成标准：**

- 故意制造数字错误、漏条款和断证据链时，QC 能拦截。
- QC 结果可定位问题对象和修复原因。

### Task 16：实现 LLM Reviewer 和人工审核

**Files:**
- Create: `worker/app/qc/llm_reviewer.py`
- Create: `backend/app/api/reviews.py`
- Create: `frontend/src/app/tasks/[taskId]/review/page.tsx`
- Test: `tests/worker/test_llm_reviewer.py`

**工作内容：**

- 对事实与解读进行二次审查，重点检查过度解释、范围扩大、条件遗漏和绝对化表达。
- 页面展示问题、证据、建议修改和原始内容。
- 支持人工通过、退回重跑、修改、锁定。
- 人工修改必须保留修改人、时间、修改前后版本和理由。

**完成标准：**

- 未通过审核的任务无法进入 `READY`。
- 通过并锁定的内容不会被后续自动重跑覆盖。

---

## 八、实现 Workflow 和 API

### Task 17：实现核心 API

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/api/tasks.py`
- Create: `backend/app/api/documents.py`
- Create: `backend/app/api/regulations.py`
- Create: `backend/app/api/articles.py`
- Create: `backend/app/api/interpretations.py`
- Create: `backend/app/api/evidence.py`
- Create: `backend/app/api/reports.py`
- Test: `tests/backend/test_api_contracts.py`

**工作内容：**

- 实现创建任务、上传文件、查询状态、查询法规、查询条款、查询解读、查询证据和生成报告接口。
- 所有长任务返回 Task ID，前端通过状态接口或 SSE 获取进度。
- API 响应统一返回 `data`、`request_id`、`error` 和版本信息。
- 前端不得直接调用模型服务。

**完成标准：**

- 使用 API 可以完成 Case 001 的完整数据流。
- 错误请求有稳定错误码，不能返回堆栈或密钥。

### Task 18：实现 Workflow Orchestrator

**Files:**
- Create: `worker/app/workflow/orchestrator.py`
- Create: `worker/app/workflow/jobs.py`
- Create: `backend/app/api/workflow.py`
- Test: `tests/worker/test_workflow_orchestrator.py`

**工作内容：**

- 编排 `S1 → S2 → S3 →（可选 S5）→ S4 → QC → Render`；新旧规比较任务对新规和旧规各自执行 S1–S3。
- 每个节点输入来自数据库中的上游版本，输出写入独立版本。
- 支持节点重跑、取消、超时、重试和失败恢复。
- 允许人工审核作为 QC 与发布之间的闸门。

**完成标准：**

- 上传后无需人工运行脚本即可完成整条流程。
- 任一节点失败时，用户能看到失败位置、原因和可执行操作。

---

## 九、实现真实网页

### Task 19：实现网站基础布局和任务入口

**Files:**
- Create: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/page.tsx`
- Create: `frontend/src/app/tasks/page.tsx`
- Create: `frontend/src/components/AppShell.tsx`
- Create: `frontend/src/components/TaskStatusBadge.tsx`
- Test: `tests/frontend/task-entry.spec.ts`

**工作内容：**

- 首页说明产品只做外规解读，并提供机构类型入口。
- 任务列表显示名称、机构类型、法规、状态、更新时间和审核状态。
- 新建任务时选择机构类型、业务范围、地域、解读时点并上传文件。
- 页面显示输入限制、证据边界和待确认提示。

**完成标准：**

- 用户不看文档也能完成新建任务。
- 任务刷新后状态和历史结果仍然存在。

### Task 20：实现 Workflow 进度页

**Files:**
- Create: `frontend/src/app/tasks/[taskId]/workflow/page.tsx`
- Create: `frontend/src/components/WorkflowTimeline.tsx`
- Create: `frontend/src/components/FailureRecoveryPanel.tsx`
- Test: `tests/frontend/workflow.spec.ts`

**工作内容：**

- 展示 S1、S2、S3、S4、QC、Render 的状态、耗时和输出摘要。
- 展示失败节点、错误信息、重试和重跑入口。
- 对 OCR、适用性不确定、证据缺失和人工审核分别显示警告。

**完成标准：**

- 页面状态与后端真实状态一致。
- 任务失败和恢复流程可以在浏览器中完成。

### Task 21：实现法规解读阅读页

**Files:**
- Create: `frontend/src/app/tasks/[taskId]/result/page.tsx`
- Create: `frontend/src/app/tasks/[taskId]/articles/[articleId]/page.tsx`
- Create: `frontend/src/components/RegulationOverview.tsx`
- Create: `frontend/src/components/ArticleInterpretation.tsx`
- Create: `frontend/src/components/EvidenceDrawer.tsx`
- Create: `frontend/src/components/InstitutionApplicabilityCard.tsx`
- Test: `tests/frontend/result-navigation.spec.ts`

**工作内容：**

- 左侧法规目录，中间解读正文，右侧证据链。
- 支持从整体解读跳到条款，从 Requirement 跳到 Article 和原文页码。
- 当存在已核验的新旧规时，展示新规、旧规、条款映射、变化类型和变化证据；缺少条件时展示待补充原因。
- 条款页显示原文、解读、核心要求、关联条款、证据和待确认项。
- 显示当前机构类型及适用性结论，不把机构画像写进监管原文。
- 支持搜索法规、条款、监管要求和解读。

**完成标准：**

- 所有可点击引用都能跳转到正确对象。
- 刷新、复制链接、返回上一步不会丢失阅读位置。

### Task 22：实现审核页和报告中心

**Files:**
- Create: `frontend/src/app/tasks/[taskId]/review/page.tsx`
- Create: `frontend/src/app/reports/page.tsx`
- Create: `frontend/src/components/ReviewDiff.tsx`
- Create: `frontend/src/components/ReportDownloadButton.tsx`
- Test: `tests/frontend/review-report.spec.ts`

**工作内容：**

- 展示 QC 问题、原文、解读、证据和人工修改入口。
- 展示报告生成状态、版本、审核状态和下载按钮。
- 未通过 QC 或未锁定的结果不能标记为正式报告。

**完成标准：**

- 用户可以从审核页修复或退回任务，并从报告中心下载已发布版本。

---

## 十、实现 HTML、Word 和内容一致性

### Task 23：实现 Content Package 和 HTML Renderer

**Files:**
- Create: `backend/app/render/content_package.py`
- Create: `frontend/src/lib/rendering.ts`
- Create: `tests/render/test_html_content_consistency.py`

**工作内容：**

- HTML 只渲染已审核 Content Package，不重新生成解读文本。
- 实现法规首页、监管速览、核心要求、条款详情和证据面板。
- 使用稳定 ID 路由，不使用展示文本作为 URL 主键。
- 做页面完整性、路由、锚点、证据跳转和刷新测试。

**完成标准：**

- HTML 页面可独立打开和刷新。
- HTML 中显示的文本与数据库锁定版本一致。

### Task 24：实现 Word Renderer

**Files:**
- Create: `backend/app/render/word_renderer.py`
- Create: `backend/app/api/reports.py`
- Test: `tests/render/test_word_renderer.py`

**工作内容：**

- 从同一个 Content Package 生成 DOCX。
- 固定报告结构：封面、法规概览、适用性、核心要求、逐条解读、证据来源、待确认事项和 QC 状态。
- 不在 Renderer 中重新调用模型或改写内容。
- 保存报告版本、生成时间、输入内容版本和下载记录。

**完成标准：**

- Word 可打开，章节、条款顺序、数字和证据与 HTML 一致。
- HTML 与 Word 的内容一致性自动检查通过。

---

## 十一、测试、数据安全和发布

### Task 25：建立 Benchmark 和自动化测试体系

**Files:**
- Create: `benchmarks/cases/`
- Create: `benchmarks/gold/`
- Create: `tests/e2e/complete-flow.spec.ts`
- Create: `tests/quality/benchmark_runner.py`
- Create: `docs/TEST_REPORT.md`

**工作内容：**

- 在 Case 001 基础上增加不同机构类型和不同版式的法规样本。
- 覆盖原生 PDF、扫描 PDF、缺失日期、复杂条款、否定词、例外、数字和跨条款引用。
- 建立字段级准确率、条款召回率、数字准确率、证据覆盖率、人工退回率和渲染一致性指标。
- 自动执行上传、解析、S1–S4、QC、HTML、Word 下载的端到端测试。

**完成标准：**

- 每次代码或 Prompt 变更都能重新跑 Benchmark。
- 质量指标、失败案例和人工确认项有留档。

### Task 26：实现权限、隐私和安全控制

**Files:**
- Create: `backend/app/auth/`
- Create: `backend/app/middleware/audit_log.py`
- Create: `backend/app/security/file_policy.py`
- Test: `tests/security/test_access_control.py`

**工作内容：**

- 实现用户登录、角色、任务访问控制和机构空间隔离。
- 文件下载使用授权接口，不暴露永久公开 URL。
- 日志中禁止写入法规全文、模型密钥和敏感用户数据。
- 对上传文件做类型校验、大小限制、恶意文件扫描和下载头设置。
- 记录谁创建、查看、修改、审核和下载了结果。

**完成标准：**

- 用户无法访问其他机构或其他用户的任务。
- 权限、文件和审计测试通过。

### Task 27：实现可观测性和运维能力

**Files:**
- Create: `backend/app/observability/metrics.py`
- Create: `backend/app/observability/logging.py`
- Create: `docs/OPERATIONS.md`
- Create: `scripts/backup.sh`
- Test: `tests/operations/test_health_checks.py`

**工作内容：**

- 记录任务耗时、节点成功率、模型调用次数、Token/成本、错误码和队列积压。
- 为数据库、存储、Redis、模型 Provider 和 Worker 增加健康检查。
- 设计备份、恢复、失败重试和人工介入流程。
- 为模型 Provider 超时、限流、无效 JSON 和服务不可用提供降级提示。

**完成标准：**

- 运维人员能定位一个失败任务的节点、错误和输入版本。
- 数据库和文件备份可以在测试环境恢复。

### Task 28：部署、试运行和最终验收

**Files:**
- Create: `Dockerfile.frontend`
- Create: `Dockerfile.backend`
- Create: `Dockerfile.worker`
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/deploy.yml`
- Modify: `README.md`
- Create: `docs/RELEASE_CHECKLIST.md`

**工作内容：**

- 部署前端、API、Worker、数据库、队列和文件存储。
- 配置环境变量、域名、HTTPS、数据库迁移、日志和备份。
- 在准生产环境跑 Case 001 以及全部 Benchmark。
- 邀请至少一名具备监管文件审阅经验的人进行人工验收。
- 记录已知限制：OCR 置信度、未确认适用性、无法确认版本关系、模型不确定性。

**最终完成标准：**

- 用户能从浏览器完成完整闭环，不需要开发者手工执行脚本。
- 失败任务可以恢复，审核后的内容可锁定和追溯。
- HTML、Word、API 返回内容一致。
- QC 未通过时不能发布。
- 生产环境有备份、日志、权限和回滚方案。

---

## 用户确认后的单一连续实施顺序

## 当前执行状态（2026-08-21）

- 第 1 步：已完成，产品边界、金融机构类型和只做外规解读已冻结。
- 第 2 步：已完成（本任务非 S5），用户提供的 2017 年版 PDF 已登记并可做正文测试；2015 年版未提供，S5 按用户要求跳过。
- 第 3 步：已完成，信息架构与用户路径已冻结。
- 第 4 步：已完成，按附件三栏工作台结构完成黑色顶部栏、黑色左侧导航、白底内容区、德勤绿交互和可点击浏览视图；网页名称冻结为“外规解读智能体工作台”。
- 第 5 步：已完成，已冻结 React+Vite、FastAPI、PostgreSQL、Redis+Celery、S3/MinIO、可替换模型 Provider、异步 Workflow 和 Docker Compose 部署边界。
- 下一步：第 6 步，建立代码仓库、后端开发环境、CI、Docker 和健康检查。

1. 冻结机构类型、适用范围、产品边界和发布口径。
2. 确定验收法规、旧规/新规样本和人工 Gold 标准。
3. 按附件参考图冻结网站信息架构、用户流程、页面线框、视觉系统和交互规范；布局保持顶部栏、左侧任务/目录、中间内容、右侧证据链。
4. 按附件参考图完成 HTML 阅读页、Word 报告和新旧规比较结果的样式设计；只调整文字、颜色和真实业务内容，不改变三栏工作台结构。
5. 冻结技术架构、模型 Provider、文件存储、数据库、队列和部署方式。
6. 建立代码仓库、开发环境、CI、Docker 和健康检查。
7. 建立数据库、版本模型、证据模型、任务状态和审计日志模型。
8. 实现登录、机构空间、角色权限和任务访问控制。
9. 实现法规上传、文件存储、文本提取、页码定位和 OCR 兜底。
10. 实现机构类型选择、适用性规则和 S1 法规元数据识别。
11. 实现 S2 法规定位、适用范围和版本关系识别。
12. 实现 S3 条款拆解、监管规则抽取和结构化数字识别。
13. 实现 S5 新旧规比较；没有可核验旧规时保留待补充状态，不伪造比较结果。
14. 实现 S4 整体解读、逐条解读和基于 S5 的变化解读。
15. 实现 Evidence 链路、Content Package 和人工锁定版本。
16. 实现规则 QC、LLM Reviewer、人工审核、退回、修改和发布闸门。
17. 实现 Workflow、异步任务、进度展示、失败恢复和节点重跑。
18. 按已确认的视觉设计实现首页、任务页、Workflow 页、解读页、条款页、比较页、审核页和报告中心。
19. 实现 HTML Renderer、Word Renderer、下载和 HTML/Word 一致性检查。
20. 建立多机构、多版式、多风险类型 Benchmark，并完成端到端、权限、安全和回归测试。
21. 部署准生产环境，完成备份、日志、监控、模型限流和故障恢复。
22. 用真实法规和人工审阅人员验收，修复阻断问题后正式发布。

最终完成条件是：用户可以从浏览器选择金融机构类型，上传一份或两份法规，获得带适用性判断、条款解读、变化比较、证据链的 HTML 页面，并下载内容一致的 Word 报告；全过程不需要开发者手工运行脚本。
