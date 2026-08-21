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

当前版本不包含真实后端 Agent、数据库、队列、OCR、模型调用和 Word 服务端生成。后续开发会保留当前页面和 API 运行时配置，将演示数据替换为 FastAPI 后端数据，并继续实现法规上传、S1—S4、QC 和报告生成。

## 本地运行

```bash
pnpm install
pnpm run dev
```

## 第六步完整工程底座

当前工作区已建立本地全栈工程骨架：

```bash
make test
make frontend-build
make compose-config
make up
```

启动后：

- 前端：`http://localhost:8080`
- API：`http://localhost:8000/health`
- API 文档：`http://localhost:8000/docs`
- MinIO 控制台：`http://localhost:9001`

第六步只提供可启动的 API/Worker/基础设施底座；法规上传、数据库迁移、OCR、S1—S4、QC 和报告生成在后续步骤实现。

## 重要说明

- 不要把真实 API Key 写入仓库或前端环境变量。
- 原始法规、解读结果和证据链的后端持久化将在后续工程步骤实现。
- 当前案例按用户要求暂不启用 S5 新旧规比较。
