# Workflow Orchestrator Specification v1.0

---

# 1. 模块定位

## 1.1 模块名称

**工作流编排引擎（Workflow Orchestrator）**

英文：

`Workflow Orchestration Engine`

---

# 1.2 核心目标

Workflow Orchestrator负责协调外规解读 Agent 全流程运行，使：

- 输入文件；
- AI Skill；
- QC模块；
- Render模块；
- 人工审核；

形成完整、可追踪、可恢复的业务流程。

---

# 1.3 核心问题

Workflow Orchestrator解决：

> 一个外规解读任务如何从上传文件，到最终生成报告，并且全过程可监控、可恢复、可审计。

---

# 1.4 核心能力

包括：

- Workflow定义；
- Task管理；
- Skill调度；
- 状态管理；
- 数据传递；
- 异常处理；
- 任务恢复；
- 人工审核路由；
- 日志记录。

---

# 2. Workflow Orchestrator在整体架构中的位置

```text id="workflow_arch"

用户提交任务

        ↓

Workflow Orchestrator

        ↓

 ┌──────────────┐
 │ S1 文件解析   │
 └──────────────┘

        ↓

 ┌──────────────┐
 │ S2 法规识别   │
 └──────────────┘

        ↓

 ┌──────────────┐
 │ S3 条款拆解   │
 └──────────────┘

        ↓

 ┌──────────────┐
 │ S4 外规解读   │
 └──────────────┘

        ↓

 ┌──────────────┐
 │ S5 版本比较   │
 └──────────────┘

        ↓

 ┌──────────────┐
 │ S6 内容编排   │
 └──────────────┘

        ↓

QC Engine

        ↓

Render Layer

        ↓

最终输出

```

---

# 3. Workflow设计原则

---

# 3.1 状态驱动原则

系统运行状态必须显式保存。

禁止：

> 根据页面显示判断任务状态。

---

所有任务必须有：

```text id="state"

task_id

workflow_status

current_step

step_status

```

---

# 3.2 节点独立原则

每个Skill：

独立运行。

输入：

结构化对象。

输出：

结构化对象。

---

禁止：

S4直接调用S3内部逻辑。

---

# 3.3 可恢复原则

任何节点失败：

不得导致整个任务丢失。

例如：

S4失败：

不需要重新执行：

- S1；
- S2；
- S3。

---

支持：

```text id="resume"

Resume From S4

```

---

# 3.4 幂等原则

同一个节点重复执行：

结果可控。

例如：

重新运行：

S3。

不得生成：

两个不同版本同时生效。

---

# 3.5 人工介入原则

AI不是所有环节自动通过。

Workflow必须支持：

```text id="human_flow"

AI Processing

↓

Human Review

↓

Continue

```

---

# 4. Workflow总体流程

---

# 4.1 标准流程

```text id="main_workflow"

Step 0 创建任务

↓

Step 1 上传法规材料

↓

Step 2 文件解析(S1)

↓

Step 3 法规识别(S2)

↓

Step 4 条款拆解(S3)

↓

Step 5 外规解读(S4)

↓

Step 6 新旧规比较(S5)

↓

Step 7 内容编排(S6)

↓

Step 8 QC检查

↓

Step 9 Render输出

↓

Step 10 发布

```

---

# 5. Task对象设计

Task是整个Workflow主对象。

---

# 5.1 Task Schema

```json id="task_schema"

{
 "task_id":"",

 "task_name":"",

 "regulation_id":"",

 "workflow_id":"",

 "workflow_status":"",

 "current_step":"",

 "created_by":"",

 "created_at":"",

 "updated_at":"",

 "priority":"",

 "error_state":{},

 "checkpoint":{}

}

```

---

# 5.2 workflow_status

固定：

```text id="workflow_status"

CREATED

UPLOADING

PROCESSING

WAITING_HUMAN_REVIEW

FAILED

COMPLETED

CANCELLED

```

---

# 6. Step对象设计

每一个Skill都是一个Workflow Step。

---

# 6.1 Step Schema

```json id="step_schema"

{
 "step_id":"",

 "task_id":"",

 "skill_name":"",

 "status":"",

 "input_object_ids":[],

 "output_object_ids":[],

 "start_time":"",

 "end_time":"",

 "retry_count":0,

 "error_message":""

}

```

---

# 6.2 Step状态

```text id="step_status"

PENDING

RUNNING

SUCCESS

FAILED

WAITING_REVIEW

SKIPPED

```

---

# 7. Skill调用机制

---

# 7.1 Skill Registry

所有Skill注册：

```json id="skill_registry"

{
 "skill_id":"S3",

 "skill_name":"条款拆解",

 "version":"1.0",

 "input_schema":"RequirementInput",

 "output_schema":"RequirementOutput",

 "enabled":true

}

```

---

# 7.2 调度规则

Workflow读取：

Skill Registry。

根据：

当前Step。

调用对应Skill。

---

# 8. Workflow Definition

建议采用配置化方式。

---

示例：

```json id="workflow_definition"

{
 "workflow_id":"REG_INTERPRETATION_V1",

 "steps":[

 {
  "step":"S1",
  "next":"S2"
 },

 {
  "step":"S2",
  "next":"S3"
 },

 {
  "step":"S3",
  "next":"S4"
 }

 ]

}

```

---

# 9. 数据传递机制

---

原则：

Skill之间不直接通信。

统一通过：

Data Object。

---

例如：

S3输出：

```text id="data_flow"

Requirement Object

```

Workflow保存：

```text id="save"

Requirement ID

```

S4读取。

---

# 10. 错误处理机制

---

# 10.1 Error分类

---

## System Error

例如：

服务器异常。

处理：

自动重试。

---

## Data Error

例如：

缺少法规原文。

处理：

暂停任务。

---

## AI Output Error

例如：

JSON格式错误。

处理：

重新生成。

---

## Human Review Error

例如：

版本关系无法确认。

处理：

进入人工审核。

---

# 11. Retry机制

---

# 11.1 自动重试

适用于：

- API失败；
- 模型超时；
- 网络异常。

---

默认：

```text id="retry"

max_retry = 3

```

---

# 11.2 人工触发重跑

支持：

```text id="manual_retry"

Retry Step S4

```

---

# 11.3 禁止全流程重跑

除非：

用户主动选择。

---

# 12. Checkpoint机制

每完成一个Step保存：

```json id="checkpoint"

{
 "task_id":"",

 "completed_step":"S3",

 "output_ids":[],

 "timestamp":""

}

```

---

例如：

任务运行：

S1-S3完成。

S4失败。

恢复：

从S4继续。

---

# 13. 人工审核Workflow

---

# 13.1 Review状态

```text id="review_status"

NOT_REQUIRED

PENDING

IN_REVIEW

APPROVED

REJECTED

```

---

# 13.2 触发条件

包括：

- QC Blocker；
- 版本不确定；
- 趋势判断；
- 收紧/放宽判断；
- 法律措辞冲突。

---

# 14. Human Review Node

人工审核作为Workflow节点。

---

流程：

```text id="human_node"

AI Output

↓

QC

↓

Human Review

↓

Approve

↓

Continue

```

---

# 15. 用户操作流程

HTML平台展示：

---

# 首页

用户：

上传法规。

---

# 任务页

展示：

```text id="task_page"

任务名称

法规名称

当前状态

处理进度

```

---

# 流程页

展示：

```text id="progress"

✓ S1 文件解析

✓ S2 法规识别

✓ S3 条款拆解

处理中 S4

○ S5

○ S6

○ QC

○ 输出

```

---

# 16. 节点详情查看

用户点击：

S3。

展示：

输入：

- Article。

输出：

- Requirement。

QC：

- 数字检查；
- 条件检查。

---

# 17. Workflow日志设计

所有动作记录：

```json id="workflow_log"

{
 "log_id":"",

 "task_id":"",

 "step":"S3",

 "action":"START",

 "operator":"AI",

 "timestamp":"",

 "message":""

}

```

---

# 18. 审计追踪

金融机构场景必须保存：

- 谁上传；
- 谁审核；
- 谁修改；
- 谁发布；
- AI版本；
- Prompt版本。

---

Audit Object：

```json id="audit"

{
 "object_id":"",

 "action":"",

 "operator":"",

 "before":"",

 "after":"",

 "timestamp":""

}

```

---

# 19. Prompt版本管理

Workflow必须记录：

每次运行使用：

```text id="prompt_version"

Skill:

S4

Prompt:

v1.2

Model:

GPT-5.x

Timestamp:

```

---

避免：

同一个法规：

不同时间结果无法解释。

---

# 20. Model Routing设计

未来支持：

多个模型。

例如：

```text id="model_route"

S1 OCR

↓

OCR Model


S3规则抽取

↓

LLM A


S4解读

↓

LLM B


QC Reviewer

↓

LLM C

```

---

# 21. Workflow质量控制

---

# QC-W01 状态完整性

检查：

所有Step是否有状态。

---

# QC-W02 数据流完整性

检查：

上一节点输出。

是否满足下一节点输入。

---

# QC-W03 断点恢复测试

模拟：

S4失败。

验证：

是否从S4恢复。

---

# QC-W04 重复执行测试

验证：

重复运行：

不会产生重复数据。

---

# QC-W05 审计日志测试

验证：

所有关键操作有记录。

---

# 22. Benchmark测试

继续使用：

《金融企业呆账核销管理办法》

---

## Case 1

S3完成。

S4失败。

验证：

是否从S4恢复。

---

## Case 2

人工修改第十四条解释。

验证：

是否覆盖保护。

---

## Case 3

重新运行S5。

验证：

是否影响S4结果。

---

## Case 4

任务取消。

验证：

状态是否正确。

---

# 23. Workflow与其他模块边界

|模块|职责|
|-|-|
|S1-S6|具体AI能力|
|QC Engine|质量检查|
|Render Layer|展示生成|
|Workflow Orchestrator|流程调度|

---

# 24. 开发注意事项

---

## 24.1 不建议使用简单函数串联

错误：

```text id="bad"

runS1()

runS2()

runS3()

```

问题：

- 无状态；
- 无恢复；
- 无日志。

---

推荐：

使用：

状态机 / Workflow Engine。

---

## 24.2 所有节点必须有输入输出定义

禁止：

Skill之间传递自然语言。

---

## 24.3 支持异步任务

法规处理可能：

几十分钟。

不能阻塞页面。

---

## 24.4 前端不要轮询Skill状态

建议：

后端提供：

Task Status API。

---

# 25. API设计建议

---

## 查询任务状态

```http
GET /api/tasks/{task_id}/status
```

---

## 获取流程

```http
GET /api/tasks/{task_id}/workflow
```

---

## 重跑节点

```http
POST /api/tasks/{task_id}/steps/{step_id}/retry
```

---

## 人工审核提交

```http
POST /api/tasks/{task_id}/review
```

---

# 26. Workflow完成标准

完成后，实现：

## 任务管理

- 创建任务；
- 查询任务；
- 删除任务。

---

## 流程管理

- 自动执行；
- 节点跳转；
- 失败恢复。

---

## 人机协同

- 自动审核；
- 人工介入；
- 修改锁定。

---

## 平台稳定性

- 状态可追踪；
- 数据不丢失；
- 节点可重跑；
- 全流程可审计。

---

# 27. 外规解读Agent完整技术闭环

至此形成：

```text id="complete_arch"

输入

↓

Workflow Orchestrator

↓

S1 文件解析

↓

S2 法规识别

↓

S3 条款拆解

↓

S4 外规解读

↓

S5 新旧规比较

↓

S6 内容编排

↓

QC Engine

↓

Render Layer

↓

HTML平台

+

Word报告

```

---

# 28. 下一阶段

完成 Workflow Orchestrator 后，下一阶段建议进入：

# 《外规解读 Agent PRD v1.0》

将前面所有设计整合成开发团队可执行文档：

包括：

1. 产品定位；
2. 用户角色；
3. 页面原型；
4. 功能模块；
5. Agent架构；
6. Skill Specification；
7. 数据库设计；
8. API设计；
9. 前端设计；
10. 后端设计；
11. 开发里程碑；
12. MVP范围。

该文档将作为真正交付给开发团队的总需求文档。