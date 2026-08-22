# 第16项验收报告：真实法规、人工复核闸门与正式发布

日期：2026-08-22
验收对象：CASE-001《金融企业呆账核销管理办法（2017年版）》
验收环境：本机准生产 Docker Compose，访问地址 `http://127.0.0.1:18080/`

## 一、工程链路验收结果

本次使用真实 4 页 PDF 执行了从浏览器后端入口到异步 Worker 的真实链路：

- API `/health`：通过。
- API `/ready`：通过；PostgreSQL 和 Redis 均为 connected。
- Web `/api/health` 反向代理：通过。
- PDF 上传和持久化解析：通过；页数 4，条款数 25。
- 异步 Workflow：通过；进度 100%。
- S1：completed。
- S2：completed。
- S3：completed。
- S4：completed。
- S5：skipped；因为当前没有可核验的 2015 年旧规，未生成比较结论。
- 结构化监管要求：56 条。
- 逐条解读：25 条。
- Evidence：25 条。
- 规则 QC：正常进入 `blocked`，共发现 109 个发布阻断项。
- LLM Reviewer：正常返回 `not_configured`，没有把规则生成内容冒充模型复核结果。

## 二、自动化回归结果

- Python 测试：`37 passed`。
- Benchmark：`6 cases / 20 assertions / 0 asset errors`，状态 `passed`。
- Python 编译检查：通过。
- `git diff --check`：通过。
- 准生产 Compose 配置解析：通过。
- 容器状态：API、Web、PostgreSQL、Redis、Worker 均 healthy；MinIO、Prometheus、PostgreSQL backup 容器运行中。

## 三、为什么还没有正式发布

第16项的工程验收已经通过，但正式发布闸门按设计仍然没有通过。当前阻断不是系统故障，而是必须由人工或正式来源补齐的业务事实：

1. 提供的 PDF 中没有可靠定位 `财金〔2017〕90号`，文号仍需人工对照正式监管原文确认。
2. PDF 未包含附1、附2、附3；涉及附件的结论必须保持“待补充”，不能由系统推断。
3. 56 条 Requirement 尚未逐项人工复核；25 条 Evidence 尚未人工核验；26 个 Interpretation 尚未人工复核并锁定。
4. 当前准生产环境未配置有效的 LLM API Key，因此 LLM Reviewer 只有 `not_configured` 状态。
5. 当前地址是本机回环地址，不是公网生产地址；公网域名、TLS、外部数据库/对象存储、备份恢复演练和正式监控仍需在目标部署环境完成。

因此，CASE-001 当前发布状态应为：`NOT_RELEASED`。系统可以交给内部审阅人员继续复核，但不能把当前结果作为已经正式发布的监管解读交付物。

## 四、人工验收后续动作

人工审阅人员需要在审核页完成：

1. 核对文号、发布主体、发布日期、生效日期和适用范围。
2. 补充并核验附1、附2、附3；若无法补充，明确保留附件待确认边界。
3. 逐项复核 56 条 Requirement，核对 25 条 Evidence 的页码、原文片段和源文件哈希。
4. 逐项复核并锁定 26 个 Interpretation。
5. 重新运行 QC；只有 QC 通过且生成 `HUMAN_LOCKED` Content Package 后，才允许导出和发布。
6. 如启用模型审阅，先在私有部署环境配置新的、未在聊天中暴露过的 API Key，再运行 LLM Reviewer，并由人工判断模型发现。

## 五、验收脚本

可用以下命令重放真实法规的非自动发布验收：

```bash
.venv/bin/python ops/acceptance_smoke.py \
  --pdf 'benchmarks/sources/财政部关于印发《金融企业呆账核销管理办法（2017年版）》的通知.pdf' \
  --timeout 180
```

脚本只创建验收任务、运行流水线和 QC/LLM 状态检查，不会自动人工批准、锁定 Content Package 或正式发布。
