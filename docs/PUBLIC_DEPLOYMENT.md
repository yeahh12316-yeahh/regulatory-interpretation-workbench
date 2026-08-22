# 公网部署方案

## 当前采用的免费架构

- 前端：GitHub Pages，仓库 `yeahh12316-yeahh/regulatory-interpretation-workbench`。
- 后端 API：Render Free Web Service。
- Workflow：API 内联执行，不部署独立 Worker。
- 数据库：Render Free PostgreSQL。
- 队列：Render Free Key Value（Redis 兼容，但不持久化）。
- 访问方式：公开匿名模式，无登录界面；系统为每个浏览器自动创建隔离的匿名工作空间。
- 上传文件和报告：临时文件系统，仅用于演示；重启或休眠后可能丢失。
- HTTPS：GitHub Pages 和 Render 默认提供 HTTPS；自定义域名可在对应平台继续绑定。

## 为什么不能把 API Key 放进 GitHub

GitHub Pages 的构建产物和前端 JavaScript 对所有访问者可见。`VITE_API_BASE_URL` 可以作为 GitHub Actions Repository Variable，但 `LLM_API_KEY` 只能作为 Render Secret，不能放入仓库、前端环境变量、截图或聊天记录。

此前已经在会话中出现过的 API Key 应撤销并重新生成。新 Key 在 Render Blueprint 首次创建时填入 `LLM_API_KEY`。

## Render 部署

仓库根目录的 `render.yaml` 会创建 API、Worker、PostgreSQL 和 Redis。首次创建 Blueprint 时填写：

- `LLM_API_KEY`：新的 Nova API Key；
- 若平台要求其他密钥，按 Render 的 Secret 提示填写。

Render 服务正常后，API 地址以 Dashboard 显示为准。

免费版的重要限制：

- Web Service 连续 15 分钟无请求会休眠，首次访问可能需要等待约 1 分钟；
- Free PostgreSQL 只有 1GB，并在创建后 30 天到期；
- Free Key Value 不持久化，重启后队列数据会丢失；
- 免费 Web Service 无持久化磁盘；
- 19 页扫描法规的 OCR 和长流程会占用 Web 请求时间，适合小规模验证，不适合作为稳定生产服务。

Render 服务正常后，API 地址以 Dashboard 显示为准：

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

## 公开匿名模式的边界

公开匿名模式通过 `PUBLIC_GUEST_MODE=true` 自动创建浏览器级匿名工作空间，保持网站打开即用且不显示登录界面。匿名令牌保存在当前浏览器中，其他浏览器不会看到该工作空间的数据。该模式仍适合公开验证，不应上传真实敏感法规、客户资料或正式生产数据。

## 仍需人工完成的生产验收

公网服务创建成功不等于正式发布完成。还需要实际验证：

1. GitHub Pages 能从浏览器调用 Render API，CORS 不报错。
2. 上传真实法规后，API 内联完成 S1—S4；免费版不部署独立 Worker。
3. LLM Reviewer 使用新 Key 返回真实模型状态。
4. PostgreSQL 备份和恢复演练完成。
5. 26 个 Interpretation、56 个 Requirement 和 25 个 Evidence 完成人工复核和锁定。
6. QC 通过并生成 `HUMAN_LOCKED` Content Package 后，才能正式发布报告。

本免费配置是“可公开访问的验证版”，不是承诺数据长期保存的生产版。若后续需要稳定保存法规、报告、备份和异步 Worker，再切回付费 Render 配置或迁移到 Oracle Always Free VM。
