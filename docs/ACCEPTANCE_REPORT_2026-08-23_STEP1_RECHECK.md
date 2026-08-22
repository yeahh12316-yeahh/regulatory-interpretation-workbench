# 第 1 步公网真实上传闭环复验报告

日期：2026-08-23  
结论：第 1 步已重新完成公网验收；本报告 supersedes 2026-08-22 关于“缺少旧规、S5 跳过”的旧结论。

## 公网验收对象

- 前端：[GitHub Pages](https://yeahh12316-yeahh.github.io/regulatory-interpretation-workbench/)
- 后端：[Render API](https://regulatory-interpretation-api.onrender.com)
- 当前版本：`f3030fe`
- 用户提供旧规：`金融企业呆账核销管理办法(财金〔2015〕60号).pdf`
- 旧规解析结果：11 页、26 条款、SHA-256 `5e46bc7efb4736fc1a99c80c35c9afb35cf031c14d8015d0aa714a756a461956`

## 真实浏览器链路

在无登录匿名公开工作空间中完成：

1. 载入当前 2017 年版任务；
2. 进入“版本比较”，点击“补充旧规原文”；
3. 上传用户提供的 2015 年 PDF，确认显示 11 页、26 条款和哈希；
4. 自动完成 S1—S4，得到 56 条 Requirement、25 条逐条 Interpretation；
5. 确认版本关系并运行 S5，生成 27 条变化（新增 1、删除 2、修改 24、未变化 0）；
6. 刷新页面，任务、证据、S1—S5 和 27 条变化仍然存在。

最终 Workflow 页面状态：S1、S2、S3、S4、S5 均为 `completed`，进度 100%；浏览器控制台无 error/warn。

## 本次修复的真实问题

- 将 Safari `Load failed` / 网络失败映射为可理解的可重试提示，并为匿名会话、准备检查、GET 和上传增加冷启动/网关重试；
- 上传使用稳定 `upload_id` 和幂等请求，避免重试重复创建任务；
- 上传成功后自动启动 S1—S4，并关闭登记弹窗回到真实任务；
- 任务列表点击现在同步切换 `pipelineTaskId`、法规 ID、Workflow 和结果，避免旧任务串用；
- 旧规按 `version_role=previous` 挂接到当前法规，不覆盖当前版本；
- S5 关系未确认时显示 `blocked`，确认并比较后同步把 Workflow S5 节点改为 `completed`；
- 解析器不再被后续附件标题覆盖，旧规法规标题识别已修正。

## 其他验证

- 后端测试：43 passed；
- 前端测试：5 passed；
- Vite 生产构建：通过；
- GitHub Actions：backend-worker、frontend、compose-smoke、Pages 部署均通过；
- 用户 PDF 未提交到 Git，仅用于本次明确授权的公网验收。

第 2 步尚未开始；人工 QC、真实 LLM Reviewer、正式内容包锁定和正式发布仍属于后续步骤，不能因第 1 步完成而提前宣称完成。
