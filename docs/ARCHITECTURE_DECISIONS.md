# 外规解读智能体工作台技术架构决策

版本：v1.0  
更新时间：2026-08-21  
适用范围：第一版真实可用网站的技术底座；不包含第 6 步 Agent 业务实现。

## 1. 架构结论

采用前后端分离、异步 Worker、证据可追溯的数据架构：

```text
浏览器
  ↓ HTTPS / REST（结果读取、任务操作、进度轮询）
React + Vite Web
  ↓
FastAPI API
  ├── PostgreSQL：任务、法规、条款、解读、证据、QC、审计
  ├── S3 兼容对象存储：原始 PDF、页图、报告文件
  └── Redis：队列、锁、短期进度缓存
        ↓
Celery Worker + 自研 Workflow 状态机
  ├── PDF 文本解析 / OCR
  ├── S1—S4（S5 受证据闸门控制）
  ├── QC Engine
  └── HTML / Word Render Layer
        ↓
可替换的 OpenAI-compatible Model Provider
```

当前已验收的 React+Vite 工作台继续作为 Web 前端，不迁移到 Next.js。该工作台属于登录后的数据密集型应用，不依赖 SEO 或服务端渲染；保留现有前端可避免破坏第 4 步已确认的三栏布局和交互。

## 2. 已冻结的技术选型

| 层 | 第一版选择 | 冻结原因 | 后续替换边界 |
|---|---|---|---|
| Web 前端 | React + Vite + JavaScript/TypeScript 渐进迁移 | 当前高保真工作台已基于 React+Vite；适合复杂交互和内部部署 | 不改变 API 合同即可迁移 Next.js |
| API | Python FastAPI | 适合文件处理、AI 调用、异步任务和类型化接口 | 业务逻辑不得写入前端 |
| 数据库 | PostgreSQL 16 | 关系数据、JSONB、外键、版本和审计均需要 | 仅通过 Repository/迁移层访问 |
| 队列 | Redis 7 + Celery Worker | 支持长任务、重试、超时和并发 Worker | 规模扩大后可迁移 Temporal，保持 Workflow 状态合同 |
| 文件存储 | S3 兼容接口；本地 MinIO，生产 S3/OSS | 原始文件、页图和报告不能放数据库或前端目录 | 只替换 StorageProvider，不改变证据定位字段 |
| 模型调用 | OpenAI-compatible Provider Adapter | 便于切换 OpenAI、企业私有模型或国产兼容接口 | S1—S4 只依赖 Provider 接口，不读取具体 SDK |
| PDF 解析 | 原生文本优先，OCR 兜底 | 可保留页码、段落和字符定位；扫描件必须标记 OCR | Parser 输出统一 ParsedDocument |
| 部署 | Docker Compose 起步，反向代理 HTTPS | 适合第一版内网/单机部署和可复现启动 | 后续可迁移 Kubernetes，不改变服务职责 |

## 3. 服务职责边界

### Web 前端

- 展示任务、法规目录、解读、证据链、QC 状态和报告下载。
- 只保存界面状态，不保存法规原文和模型密钥。
- 上传文件使用 API 返回的资源 ID；不直接写数据库或对象存储。
- 当前页面可用的演示数据，进入第 6 步后替换为 API 数据，不改变三栏信息架构。

### API

- 负责认证、机构空间、任务、文件、结果读取和人工操作。
- 创建任务、上传文件、读取结果属于短请求。
- 解析、条款拆解、解读、QC 和报告生成统一创建异步 Workflow，不在 HTTP 请求内等待模型完成。
- API 不直接修改 `Article.original_text`；人工修改必须产生新版本和审计事件。

### Worker

- 消费带 `task_id`、`workflow_step`、`input_version` 的任务消息。
- 每个节点幂等、可重试、可记录错误；重复执行不得覆盖已锁定结果。
- 先写结构化对象和证据，再允许 S4 生成解读。
- S5 只有在新旧文件、版本关系和两侧解析结果均通过 QC 后才允许进入队列。

### Render Layer

- HTML 与 Word 都只读取已确认的统一内容数据，不再次调用模型。
- 两种交付物必须共享同一 `ContentPackage` 和证据 ID。
- 页面链接、页码、段落、字符区间和报告章节均由结构化导航对象生成。

## 4. 数据与证据不变量

1. 原始法规文件以 SHA-256 作为内容身份，写入对象存储后不可覆盖。
2. `SourceDocument → Regulation → Article → Requirement → Interpretation → Evidence` 是最小可追溯链。
3. `FACT`、`OFFICIAL`、`INTERPRETATION`、`REFERENCE` 分开存储和展示，不能仅靠文案颜色区分。
4. 任何数字、日期、文号、否定词、条件和例外都必须保留来源定位。
5. 没有可核验旧规时，S5 数据对象可以存在，但状态只能是 `NOT_ENABLED` 或 `NEEDS_SOURCE`，不能生成差异结论。
6. QC 阻断项未关闭时，任务不得进入 `READY`，也不得生成正式 Word 报告。

## 5. 异步任务和状态边界

| 操作 | 处理方式 | 结果 |
|---|---|---|
| 创建任务、选择机构类型 | API 同步 | 返回 `task_id` |
| 上传 PDF、哈希和基本校验 | API 同步 | 返回 `source_document_id`，状态 `UPLOADED` |
| 文本提取、OCR、S1—S4 | Worker 异步 | 前端轮询 Workflow 状态 |
| S5 | Worker 异步、证据闸门控制 | 无旧规时明确显示跳过/待补充 |
| QC | Worker 异步 | 返回 blocker、warning、review 状态 |
| HTML 阅读 | API 读取已确认 ContentPackage | 不调用模型 |
| Word 生成 | Worker 异步 | 返回 `report_id` 和受保护下载地址 |

第一版进度读取先采用 REST 轮询，避免引入 WebSocket 运维复杂度；后续需要实时推送时可在不改变 Workflow 状态的前提下增加 SSE。

## 6. 配置和密钥边界

- 所有环境差异通过环境变量注入，模板见项目根目录 `.env.example`。
- 不把 API Key、数据库密码、对象存储密钥、用户文件或真实法规数据提交到 Git。
- `LLM_PROVIDER`、`LLM_BASE_URL`、`LLM_MODEL`、超时、重试和 JSON 输出要求由 Provider Adapter 管理。
- 本地开发默认 MinIO、PostgreSQL、Redis；生产环境可替换为企业已有服务。
- 生产部署必须配置 HTTPS、备份、对象存储版本保护、日志保留和健康检查。

## 7. 当前不在第 5 步实现的内容

- FastAPI 路由和鉴权实现；
- PostgreSQL 迁移和 ORM 模型；
- Celery 任务和 Worker；
- S1—S6 模型 Prompt、OCR 和报告生成；
- 企业 SSO、生产域名、云资源和真实模型密钥。

这些内容进入第 6 步及之后实现。本步只冻结它们之间的接口和责任边界，避免后续边开发边改架构。

## 8. 第 5 步验收标准

- 前后端、Worker、数据库、队列、对象存储和模型 Provider 的职责边界已经明确。
- 当前 React+Vite 页面无需迁移即可作为前端入口。
- 配置模板不包含真实密钥，且能表达开发、测试和生产的差异。
- 原始文件不可变、结果可版本化、证据可双向定位、S5 可被证据闸门阻断。
- 第 6 步可以按本文件直接建立代码骨架，不需要重新讨论技术选型。
