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
- 单团队工作台直接进入，不设置第一版强制登录；页面保留机构类型、任务状态、法规解读和证据链核心入口。

当前版本按单团队内部使用/私有部署定位，第一版前端不设置登录和角色权限门槛，直接进入工作台。第九步已完成法规 PDF 上传、解析、版本登记和条款页码/行号定位；第十步已接入可运行的 S1—S4 证据约束流水线，结果写入 PostgreSQL 并标记为待人工复核。后端 JWT、机构空间和角色权限代码保留为后续多人协同或公网部署时启用的基础。

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

当前全栈底座可启动 API/Worker/基础设施；第八步补充了认证与机构访问控制，第九步完成法规输入，第十步完成 S1—S4 监管侧解读结果写入。当前默认使用证据约束的规则生成模式，所有结果需人工复核；QC、异步重跑、报告生成和公网部署仍按路线在后续步骤实现。

## 重要说明

- 不要把真实 API Key 写入仓库或前端环境变量。
- 原始法规、Requirement、Interpretation 和 Evidence 已由后端持久化；正式发布前仍需完成 QC 和人工锁定闸门。
- 当前案例按用户要求暂不启用 S5 新旧规比较。
