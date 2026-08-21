# 外规解读智能体工作台：新会话交接记录

更新时间：2026-08-22

## 0. 给新会话的首要指令

这是一个已经完成第 1—10 步的外规解读智能体项目。新会话应先阅读本文件、`docs/IMPLEMENTATION_STATUS.md` 和当前代码，不要重复设计第 1—10 步，也不要擅自跳到第 12 步。

当前用户的明确要求是：

1. 按开发路线顺序推进，不绕步、不跳步。
2. 产品只做“外规解读”，不做外规内化、制度映射、差距分析、整改管理或审计闭环。
3. 目标是形成真实可用的网站，不是只做静态 Demo。
4. 当前定位为单个团队内部使用或私有部署，第一版直接进入工作台，不强制登录。
5. 2017 年版《金融企业呆账核销管理办法》进入当前任务；没有 2015 年旧版，因此 S5 不启用。
6. 下一步只能从第 11 步开始；在用户明确要求前，不进入第 12 步或额外扩展。

## 1. 产品最终目标

产品名称固定为：**外规解读智能体工作台**。

目标是让金融机构用户上传一份正式外部监管文件后，能够完成：

法规登记 → 原文解析 → 版本登记 → 条款定位 → 机构适用性判断 → 监管要求抽取 → 条款解读 → 证据链绑定 → 人工复核 → 可交付输出。

当前不承担以下工作：

- 不自动完成制度映射；
- 不做制度差距分析或整改建议；
- 不替代合规、法务或业务人员作最终判断；
- 不在缺失权威原文时补造条款、日期、数字或结论；
- 不启用没有旧版原文支撑的 S5 新旧规比较。

## 2. 用户已经确认的产品与交互决策

### 2.1 页面布局

采用用户附件确认的稳定三栏工作台：

- 顶部：产品标题和少量工作台操作；
- 左栏：任务列表、法规目录；
- 中栏：法规概览、适用性判断、监管要求、条款解读；
- 右栏：证据链、原文定位、添加证据。

### 2.2 视觉规范

- 顶部栏：黑色底、白色字；
- 左侧导航：黑色底、白色字；
- 中间内容：白底、黑字；
- 证据轨道和主要交互：德勤绿；
- 使用德勤白色 Logo，文件位于 `public/assets/deloitte-logo-white.png`；
- 页面标题必须是“外规解读智能体工作台”，不能替换成其他产品名；
- DORA 等示例数据已经移除，不能再次作为真实业务结果展示。

### 2.3 登录、机构空间和权限

用户最终确认：当前目标是单团队内部使用或私有部署，第一版不需要在前端展示登录、机构空间、角色权限等功能。因此：

- 前端直接进入工作台；
- 顶部不展示强制登录控件、预览用户、机构切换和权限状态；
- 后端认证、机构和角色代码保留，供未来多人协同或公网部署使用；
- `PRIVATE_MODE=true` 时，私有单团队部署可以直接进入工作台。

这不是忘记实现登录，而是根据用户确认有意将其从第一版前端入口后置。

## 3. 按步骤回顾：已经完成的工作

### 第 1 步：冻结产品边界——已完成

已确认面向多类型金融机构，只做外规识别、适用性判断、条款拆解、外规解读、证据链和交付物基础能力。

没有把任务扩展为完整的外规内化平台，也没有把制度映射、Gap、整改、审计闭环塞入第一版核心闭环。

### 第 2 步：验收法规与 Gold——已完成，当前任务不做 S5

用户提供的真实文件：

`benchmarks/sources/财政部关于印发《金融企业呆账核销管理办法（2017年版）》的通知.pdf`

已完成读取和基础验收：

- 识别标题：`金融企业呆账核销管理办法(2017年版)`；
- 版本：2017 年版；
- 发布日期：2017-08-31；
- 生效日期：2017-10-01；
- 页数：4 页；
- 正文条款：第 1 条至第 25 条；
- 文号：当前 PDF 中没有可靠识别结果，因此没有擅自补齐；
- 文件中提及附件，但附件正文未可靠包含在当前 PDF 内。

用户明确表示没有 2015 年旧版，因此：

- 当前不做 S5；
- 不生成新旧规差异结论；
- 不把 2015 年版本关系写成已核验事实；
- 后续只有在拿到 2015 年权威原文并完成版本关系登记后，才重新评估 S5。

真实法规 PDF 只保存在本地 `benchmarks/sources/`，不能上传到公开 GitHub 仓库。

### 第 3 步：信息架构和流程——已完成

已确定工作台核心信息架构：

左侧任务/法规目录 → 中间解读工作区 → 右侧证据链。

已确定核心对象：任务、法规、法规版本、原文文件、条款、监管要求、解读、证据、版本关系、质量检查和审计日志。

### 第 4 步：页面实现与浏览验收——已完成

已完成并在浏览器中验证：

- 黑色顶部栏和左侧导航；
- 白底黑字内容区；
- 德勤绿证据轨道；
- Deloitte Logo；
- 三栏固定布局；
- 任务列表和法规目录；
- 证据卡片；
- “查看定位”；
- “添加证据”；
- 左侧栏展开/收起；
- 页面标签、搜索和操作反馈。

高保真原型图：

`docs/prototypes/外规解读智能体工作台-v2.png`

本地预览通常使用：

`http://127.0.0.1:5173/`

### 第 5 步：技术架构冻结——已完成

技术基线：

- 前端：React + Vite；
- API：FastAPI；
- 数据库：PostgreSQL；
- 异步基础设施：Redis + Celery；
- 文件对象存储：S3/MinIO；
- 模型调用：可替换 Provider；
- 部署：Docker Compose；
- 前端公开预览：GitHub Pages；
- 后端不能依赖 GitHub Pages，需单独部署公网或私有服务。

主要配置参考：

- `.env.example`；
- `docker-compose.yml`；
- `docs/ARCHITECTURE_DECISIONS.md`；
- `src/lib/runtime-config.js`。

### 第 6 步：代码骨架、开发环境、CI、Docker 与健康检查——已完成

已建立：

- `backend/` FastAPI 后端；
- `worker/` Worker 基础骨架；
- `tests/` 后端和 Worker 测试；
- 前端 Dockerfile；
- 后端 Dockerfile；
- Worker Dockerfile；
- `docker-compose.yml`；
- GitHub Actions；
- Makefile；
- 健康检查和 Worker 心跳。

重要环境事实：

- 当前本机没有 Docker CLI；
- Compose 构建、启动、健康检查和 PostgreSQL CRUD 已由 GitHub-hosted CI 完成；
- Redis、MinIO 和 Worker 业务消费逻辑仍需在后续步骤继续完善；
- “CI Compose 通过”不等于已经有公网后端服务。

### 第 7 步：数据库、版本、证据、任务状态和审计日志——已完成

SQLAlchemy 模型已覆盖：

- `Task`；
- `Organization`；
- `User`；
- `OrganizationMember`；
- `SourceDocument`；
- `Regulation`；
- `RegulationVersion`；
- `Article`；
- `Requirement`；
- `Interpretation`；
- `Evidence`；
- `VersionRelation`；
- `QCResult`；
- `AuditLog`。

已完成 Alembic 初始迁移和真实 PostgreSQL 最小 CRUD 验收。

已有基础 API：

- `POST/GET /api/tasks`；
- `POST/GET /api/regulations`；
- `POST/GET /api/source-documents`；
- `POST/GET /api/evidence`。

### 第 8 步：登录、机构空间、角色权限和任务访问控制——后端完成，前端按用户要求后置

后端已实现：

- 注册；
- 登录；
- JWT Bearer 认证；
- 当前用户；
- 机构切换；
- 成员管理；
- 角色变更；
- 任务按机构隔离；
- `owner`、`admin`、`editor`、`reviewer`、`viewer` 角色。

前端按用户最终要求：

- 不展示登录页；
- 不展示机构空间入口；
- 不展示顶部权限控件；
- 直接进入外规解读工作台。

### 第 9 步：法规上传、解析、版本登记和原文定位——已完成

上传接口：

`POST /api/regulations/import`

已实现：

- PDF 上传；
- 原文件哈希；
- 私有文件存储；
- 标题识别；
- 文号识别；
- 发布日期和生效日期识别；
- 版本标签登记；
- `Regulation`、`RegulationVersion`、`Article` 自动创建；
- 条款页码和行号/文本偏移定位；
- 原文件访问接口；
- 前端上传入口；
- 上传失败清理，避免留下孤立法规或任务记录；
- 无 API 配置时不伪造上传成功。

同一法规的现行版本会保留旧版本关系，不覆盖历史记录。

### 第 10 步：S1—S4 真实条款解读流水线——已完成

流水线服务：

`backend/app/services/interpretation_pipeline.py`

顺序固定为：

`S1 → S2 → S3 → S4`

#### S1：法规元数据确认

输出标题、机关、文号、日期、页数、条款数量、版本信息和待确认字段。

缺失文号、附件缺失等信息会保留为待确认，不使用模型常识补齐。

#### S2：机构适用性判断

输入包括：

- 机构类型；
- 业务范围；
- 地域；
- 解读时点。

输出包括：

- `DIRECTLY_APPLICABLE` 或 `NEEDS_REVIEW`；
- 机构类型匹配；
- 地域/时点匹配；
- 判断理由；
- 是否需要证据和人工复核。

规则对“商业银行—金融企业—中国境内”场景已有回归测试。

#### S3：监管要求抽取

按 Article 提取 Requirement，识别：

- `OBLIGATION`：应当、必须、须、应；
- `PROHIBITION`：不得、禁止、严禁；
- `PERMISSION`：可以、可、有权；
- `SCOPE`；
- `OTHER`。

同时尽可能结构化保留：

- 主体；
- 行为；
- 对象；
- 条件；
- 例外；
- 频率；
- 时限；
- 阈值；
- 数字表达；
- 原文片段。

#### S4：整体和逐条款解读

生成：

- 整体解读；
- 逐条款解读；
- `FACT` 内容块；
- `OFFICIAL` 内容块；
- `INTERPRETATION` 内容块；
- Article/Evidence 绑定；
- 人工复核状态。

当前所有输出均标记为 `needs_review`，避免把规则生成结果伪装成已批准的正式法律结论。

#### 第十步 API

- `POST /api/tasks/{task_id}/interpret`：执行 S1—S4；
- `GET /api/tasks/{task_id}/interpretation`：读取整体和逐条解读；
- `GET /api/tasks/{task_id}/requirements`：读取结构化监管要求。

#### 第十步前端

工作台已增加：

- “运行 S1—S4”按钮；
- S1/S2/S3/S4 状态；
- 适用性结果；
- 监管要求卡片；
- 逐条款解读卡片；
- 证据链接；
- 无后端配置时的明确提示。

公开 Pages 点击运行时会显示：

`当前公开预览未连接后端，私有部署配置 API 后才能运行 S1—S4`

这属于预期行为，不是故障。

## 4. 当前代码和文档入口

### 前端

- `src/App.jsx`：工作台主页面和运行入口；
- `src/styles.css`：三栏布局、黑白德勤绿视觉和流水线卡片；
- `src/lib/api-client.js`：前端 API 客户端；
- `src/lib/runtime-config.js`：运行时 API 配置；
- `public/assets/deloitte-logo-white.png`：德勤白色 Logo。

### 后端

- `backend/app/main.py`：FastAPI 入口；
- `backend/app/api/ingest.py`：法规上传和解析；
- `backend/app/api/pipeline.py`：S1—S4 API；
- `backend/app/api/schemas.py`：接口 Schema；
- `backend/app/services/regulation_ingest.py`：法规解析；
- `backend/app/services/interpretation_pipeline.py`：S1—S4 流水线；
- `backend/app/db/models.py`：数据库模型；
- `backend/app/core/config.py`：配置和模型 Provider 环境变量；
- `backend/migrations/versions/cf7a0d6a10f2_add_pipeline_output_metadata.py`：第十步字段迁移。

### 测试

- `tests/backend/test_regulation_ingest.py`；
- `tests/backend/test_crud_api.py`；
- `tests/backend/test_data_model.py`；
- `tests/backend/test_health.py`；
- `tests/backend/test_interpretation_pipeline.py`；
- `tests/worker/test_heartbeat.py`。

### 规范与产品文档

- `docs/IMPLEMENTATION_STATUS.md`：当前实施状态；
- `docs/PRODUCT_SCOPE.md`：产品边界；
- `docs/INFORMATION_ARCHITECTURE.md`：信息架构；
- `docs/ACCEPTANCE_CRITERIA.md`：验收标准；
- `docs/WEBSITE_STYLE_SYSTEM.md`：视觉系统；
- `docs/ARCHITECTURE_DECISIONS.md`：架构决策；
- `docs/SOURCE_REGISTER.md`：来源登记；
- `docs/prototypes/外规解读智能体工作台-v2.png`：高保真原型；
- `docs/superpowers/plans/2026-08-21-regulatory-interpretation-agent-website.md`：开发计划。

## 5. 当前部署和 Git 状态

### GitHub 仓库

仓库：

`https://github.com/yeahh12316-yeahh/regulatory-interpretation-workbench`

当前公开 Pages：

`https://yeahh12316-yeahh.github.io/regulatory-interpretation-workbench/`

公开仓库当前最新相关提交：

- `b860b1b test: cover explicit domestic applicability`；
- `06374f6 feat: add evidence-bound S1-S4 interpretation pipeline`；
- `19f4824 fix: clean failed regulation uploads`。

本地工作区当前最新提交：

- `b3ce589 test: cover explicit domestic applicability`；
- `f45074d feat: add interpretation pipeline service`；
- `a6bdb99 feat: add evidence-bound S1-S4 interpretation pipeline`。

本地和公开仓库的文件内容已同步，提交哈希不同是因为本地和公开临时工作副本分别提交。

### 已通过的自动化验收

第十步修正后的 GitHub CI：

- CI run：`32507974424`；
- backend-worker：通过；
- frontend：通过；
- compose-smoke：通过；
- PostgreSQL 健康检查和 CRUD：通过；
- S1—S4 测试：通过；
- Pages 部署：`32507974309`，通过。

首次第十步 CI 曾发现 S2 合成测试数据没有明确“中国境内”范围，已补充测试夹具并重新通过。该问题不是生产代码误判，而是测试数据不足以支持“直接适用”结论。

### 当前部署事实

- GitHub Pages 只有前端；
- 公开 Pages 没有连接真实后端；
- PostgreSQL、Redis、MinIO、Worker 尚未部署为公网服务；
- `VITE_API_BASE_URL` 尚未在公开 Pages 配置为真实后端地址；
- 真实 2017 年法规 PDF 没有进入公开仓库；
- 真正运行 S1—S4 需要私有/公网后端、PostgreSQL 和文件存储配置。

## 6. 尚未完成的事项

### 第 11 步：人工复核、质量检查与交付物导出——下一步

新会话应从这里开始，但开始前要先检查当前代码和本文件。

建议按以下顺序实现：

1. 人工复核界面
   - 对 S1 元数据进行确认或修订；
   - 对 S2 适用性结论进行确认、改为待核验或补充理由；
   - 对 S3 Requirement 的主体、行为、对象、条件、时限和例外进行逐项编辑；
   - 对 S4 FACT/OFFICIAL/INTERPRETATION 内容块进行编辑、锁定和留痕；
   - 不允许人工修改后丢失原文和证据定位。

2. 质量检查闸门
   - 检查每个结论是否绑定 Article/Evidence；
   - 检查每个 Requirement 是否保留原文片段；
   - 检查“待确认字段”是否被误标为完成；
   - 检查附件缺失、文号缺失、地域边界不明等问题是否显著提示；
   - 检查 S5 是否保持跳过状态；
   - 质量检查不通过时，不允许进入“可交付”状态。

3. 交付物最小版本
   - 外规概览；
   - 机构适用性判断；
   - 监管要求清单；
   - 条款解读；
   - 证据链和原文定位；
   - 待人工确认事项；
   - 生成 Word 或 PDF 的基础版本；
   - 导出文件需要携带生成时间、版本和复核状态。

4. 复核和交付状态
   - `waiting_review`：流水线已生成，等待人工复核；
   - `reviewing`：正在人工复核；
   - `reviewed`：人工复核完成；
   - `ready_for_export`：质量检查通过，可以导出；
   - `exported`：已生成交付物。

5. 第 11 步验收
   - 用真实 2017 年 PDF 在私有后端运行一次；
   - 验证第 1—25 条都保留原文定位；
   - 验证缺失文号和附件缺失被标记；
   - 验证 S5 仍显示“未启用/缺少 2015 年旧版”；
   - 验证人工修改、锁定、审计记录和导出结果；
   - 完成后才能考虑第 12 步。

### 第 12 步及以后：暂不开始，只记录方向

第 12 步可能涉及真实模型 Provider、异步任务、重跑、QC Engine、Redis/MinIO 业务联通和公网服务部署，但用户要求当前按步骤推进，因此本阶段不能提前实施。

特别注意：

- 不要因为 `.env.example` 中有 `LLM_API_KEY` 就声称已经接入模型；
- 不要因为 Compose 文件存在 Redis/MinIO 就声称已经完成公网部署；
- 不要把 GitHub Pages 的前端可访问性当成完整 Agent 已经公网可用。

## 7. 新会话必须保持的真实性边界

### 来源真实性

法规原文是第一证据。没有权威原文时，输出必须写明“待补充官方原文”或“需人工确认”。

### 结论真实性

必须区分：

- `FACT`：从文件中直接提取的事实；
- `OFFICIAL`：原文、官方来源或正式公开答复；
- `INTERPRETATION`：基于原文的解释性判断。

不应把解释性判断写成官方正式结论。

### 机构适用性真实性

机构类型、业务范围、地域和时点都可能影响适用性。证据不足时使用 `NEEDS_REVIEW`，不能为了让页面看起来完整而强行输出 `DIRECTLY_APPLICABLE`。

### 版本真实性

2015 年版本没有提供，不能虚构版本关系、条款变化或废止结论。

### 附件真实性

2017 年 PDF 提及附件，但当前文件没有可靠包含完整附件。涉及附件的解读必须暂停并提示补充附件。

## 8. 新会话建议的启动提示词

可以将下面内容直接复制到新会话：

> 请先读取项目目录 `/Users/yeahh/Documents/ChatGPT/外规解读agent/` 下的 `docs/HANDOFF_2026-08-22_STEP10.md`、`docs/IMPLEMENTATION_STATUS.md` 和当前 Git 状态。我们已经完成第 1—10 步，不要重复这些步骤，也不要跳到第 12 步。现在从第 11 步“人工复核、质量检查与交付物导出”开始。目标仍然是单团队内部使用/私有部署的“外规解读智能体工作台”，只做外规解读，不做制度映射、Gap、整改或审计闭环。2017 年《金融企业呆账核销管理办法》已提供，2015 年旧版缺失，S5 必须保持跳过。请先给出第 11 步的实施计划和当前代码检查结果，确认后再修改代码；任何发现的风险或阻塞马上说明。

## 9. 交接结论

截至本记录更新时间：

- 第 1—10 步已完成；
- 第 10 步 S1—S4 已实现并通过 CI、Compose 和前端浏览验收；
- 公开网站是前端工作台，不是已经接入后端的完整公网 Agent；
- 真实后端部署和模型 API 接入尚未完成；
- 第 11 步是下一步唯一应推进的开发步骤；
- 2015 年旧版、附件补充、人工复核、QC 和交付物导出仍是当前主要待办。
