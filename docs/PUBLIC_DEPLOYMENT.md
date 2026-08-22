# 公网部署方案

## 目标架构

- 前端：GitHub Pages，仓库 `yeahh12316-yeahh/regulatory-interpretation-workbench`。
- 后端 API：Render Web Service。
- 异步 Worker：Render Background Worker。
- 数据库：Render PostgreSQL。
- 队列：Render Key Value（Redis 兼容）。
- 上传文件和报告：Render API 服务的持久化磁盘 `/data/regulatory-workbench`。
- HTTPS：GitHub Pages 和 Render 默认提供 HTTPS；自定义域名可在对应平台继续绑定。

## 为什么不能把 API Key 放进 GitHub

GitHub Pages 的构建产物和前端 JavaScript 对所有访问者可见。`VITE_API_BASE_URL` 可以作为 GitHub Actions Repository Variable，但 `LLM_API_KEY` 只能作为 Render Secret，不能放入仓库、前端环境变量、截图或聊天记录。

此前已经在会话中出现过的 API Key 应撤销并重新生成。新 Key 在 Render Blueprint 首次创建时填入 `LLM_API_KEY`。

## Render 部署

仓库根目录的 `render.yaml` 会创建 API、Worker、PostgreSQL 和 Redis。首次创建 Blueprint 时填写：

- `LLM_API_KEY`：新的 Nova API Key；
- 若平台要求其他密钥，按 Render 的 Secret 提示填写。

Render 服务正常后，API 默认地址为：

```text
https://regulatory-interpretation-api.onrender.com
```

真实地址以 Render Dashboard 显示为准。先验证：

```bash
curl -fsS https://regulatory-interpretation-api.onrender.com/health
curl -fsS https://regulatory-interpretation-api.onrender.com/ready
```

## GitHub Pages API 地址

在 GitHub 仓库 Settings → Secrets and variables → Actions → Variables 中新增：

```text
VITE_API_BASE_URL=https://regulatory-interpretation-api.onrender.com/api
```

然后手动运行 `Deploy frontend workbench to GitHub Pages`，或向 `main` 推送代码触发部署。GitHub Pages 的公开地址通常为：

```text
https://yeahh12316-yeahh.github.io/regulatory-interpretation-workbench/
```

## 仍需人工完成的生产验收

公网服务创建成功不等于正式发布完成。还需要实际验证：

1. GitHub Pages 能从浏览器调用 Render API，CORS 不报错。
2. 上传真实法规后，Worker 能完成 S1—S4 异步任务。
3. LLM Reviewer 使用新 Key 返回真实模型状态。
4. PostgreSQL 备份和恢复演练完成。
5. 26 个 Interpretation、56 个 Requirement 和 25 个 Evidence 完成人工复核和锁定。
6. QC 通过并生成 `HUMAN_LOCKED` Content Package 后，才能正式发布报告。
