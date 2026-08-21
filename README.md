# 外规解读智能体工作台

公开预览地址：

<https://yeahh12316-yeahh.github.io/regulatory-interpretation-workbench/>

## 当前交付范围

当前 GitHub Pages 部署的是 React + Vite 前端工作台，包含：

- 多类型金融机构选择入口；
- 法规任务列表和法规目录；
- 2017 年版《金融企业呆账核销管理办法》示例结果页；
- 条款解读、适用性判断和证据链工作区；
- 证据上传、定位、目录收起/展开等前端交互。

当前仓库现在包含第六步的后端工程骨架：FastAPI API、Celery Worker、PostgreSQL/Redis/MinIO 的 Docker Compose 配置、健康检查和 CI 测试。但它还不是可直接进行真实法规解读的完整 Agent：法规上传、数据库业务模型、OCR、S1—S4、QC、模型 Provider 和 Word 服务端生成将在后续步骤实现。

GitHub Pages 只运行前端；后端需要在具备 Docker 或 Python 运行环境的服务器上启动，并通过 API 地址连接前端。当前 `/health` 和 `/ready` 是工程底座检查接口，不能替代真实解读接口。

## 本地运行

```bash
pnpm install
pnpm run dev
```

## 启动第六步全栈底座

```bash
cp .env.example .env
docker compose up --build
```

- 前端：`http://localhost:8080`
- API：`http://localhost:8000/health`
- API 文档：`http://localhost:8000/docs`
- MinIO 控制台：`http://localhost:9001`

## 重要说明

- 不要把真实 API Key 写入仓库或前端环境变量。
- 原始法规、解读结果和证据链的后端持久化将在后续工程步骤实现。
- 当前案例按用户要求暂不启用 S5 新旧规比较。
