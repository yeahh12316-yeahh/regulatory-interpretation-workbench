# 外规解读智能体工作台实施状态

更新时间：2026-08-21

## 当前步骤

第 1—7 步已完成；第 8 步后端能力已完成，但前端登录、机构空间和角色管理界面尚未接入，因此第 8 步整体仍进行中。本机仍未安装 Docker CLI，容器验收通过 GitHub Actions 完成。

| 步骤 | 状态 | 说明 |
|---|---|---|
| 第 1 步：冻结产品边界 | 已完成 | 面向多类型金融机构，只做外规识别、适用性、条款拆解、解读、证据和交付物 |
| 第 2 步：验收法规与 Gold | 已完成（本任务非 S5） | 用户已提供 4 页 2017 年版打印 PDF；正文第1—25条可读取；2015 年版按用户要求不纳入本任务 |
| 第 3 步：信息架构和流程 | 已完成 | 顶部栏、左侧任务/目录、中间解读、右侧证据链 |
| 第 4 步：页面实现与浏览验收 | 已完成 | 已完成黑色顶栏与左侧导航、Deloitte 官方白色 Logo、白底黑字、德勤绿交互、证据上传/定位及浏览器验收，并保存高保真原型图 |
| 第 5 步：技术架构冻结 | 已完成 | 已冻结 React+Vite 前端、FastAPI API、PostgreSQL、Redis+Celery、S3/MinIO、可替换模型 Provider、异步 Workflow 和 Docker Compose 部署边界 |
| 第 6 步：代码骨架、开发环境、CI、Docker 与健康检查 | 已完成 | 已建立 backend、worker、tests、Dockerfile、Compose、CI、Makefile、健康检查和 Worker 心跳；本地测试、Compose YAML、前端构建通过，GitHub Actions 已真实启动全栈 Compose 并通过 API/Web 健康检查 |
| 第 7 步：数据库、版本、证据、任务状态和审计日志模型 | 已完成 | 已建立 SQLAlchemy 领域模型、Alembic 首次迁移、PostgreSQL 真实连接、自动迁移和任务/法规/来源文件/证据最小 CRUD API，并通过本地与 GitHub Compose 验收 |
| 第 8 步：登录、机构空间、角色权限和任务访问控制 | 进行中 | 后端已实现注册/登录、JWT、当前用户、机构切换、成员管理、角色变更和任务组织隔离；工作台前端尚未接入登录状态、机构选择和角色管理界面 |

## 第 4 步浏览验收证据

- 页面名称：外规解读智能体工作台。
- 布局：顶部全局栏 + 左侧任务/法规目录 + 中间法规解读 + 右侧证据链。
- 颜色：顶部栏与左侧导航为黑底白字，内容区为白底黑字，证据轨道及交互统一使用德勤绿；DORA 示意数据已移除。
- 页面状态：明确显示“2017 年版已载入”“待解析”“版本比较暂不启用”。
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
- 前端缺口：`src/App.jsx` 当前仍是静态工作台，尚未调用 `/api/auth/*` 或 `/api/organizations/*`；因此浏览器中暂时看不到登录、当前机构、成员和角色管理入口。
- 当前边界：第八步前端接入完成前，不进入第九步法规上传解析。
