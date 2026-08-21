# 外规解读 Agent API Specification v1.0

---

# 1. 文档定位

## 1.1 文档目的

本文档定义外规解读 Agent 平台 API 接口规范。

用于指导：

- 前端页面开发；
- 后端服务开发；
- Workflow调用；
- AI服务调用；
- 文件服务调用。

---

# 1.2 API设计目标

API需要支持：

- 创建解读任务；
- 上传法规文件；
- 查询任务状态；
- 查看AI处理流程；
- 获取法规信息；
- 获取条款；
- 获取监管规则；
- 获取外规解读；
- 获取版本比较；
- 获取QC结果；
- 生成Word报告；
- 加载HTML页面数据；
- 人工审核。

---

# 1.3 API设计原则

---

## 原则1：资源ID驱动

所有接口使用：

```text id="api_id"

task_id

regulation_id

article_id

requirement_id

evidence_id

change_id

```

---

禁止：

使用：

- 法规名称；
- 条款名称；

作为唯一查询条件。

---

## 原则2：异步任务设计

AI任务可能耗时较长。

采用：

```text id="async"

POST 创建任务

↓

返回task_id

↓

异步处理

↓

GET查询状态

```

---

## 原则3：全过程可追踪

所有接口返回：

```json id="trace_id"

{
 "request_id":"",
 "task_id":"",
 "timestamp":""
}

```

---

# 2. API整体架构

```text id="api_arch"

Frontend

    ↓

API Gateway

    ↓

Backend Service


 ┌───────────────┐
 │ Task Service  │
 └───────────────┘

 ┌───────────────┐
 │ Workflow API  │
 └───────────────┘

 ┌───────────────┐
 │ Regulation API│
 └───────────────┘

 ┌───────────────┐
 │ AI Service API│
 └───────────────┘

 ┌───────────────┐
 │ Render API    │
 └───────────────┘

```

---

# 3. API基础规范

---

# 3.1 Base URL

示例：

```text id="base"

https://api.xxx.com/v1

```

---

# 3.2 请求格式

Content-Type：

```http
application/json
```

---

# 3.3 通用返回格式

成功：

```json id="success"

{
 "success":true,

 "data":{},

 "request_id":"xxx",

 "message":"success"
}

```

---

失败：

```json id="error"

{
 "success":false,

 "error_code":"",

 "message":"",

 "request_id":""

}

```

---

# 4. Task任务接口

---

# 4.1 创建外规解读任务

## API

```http id="create_task"

POST /api/tasks

```

---

## 请求参数

```json id="create_task_req"

{
 "task_name":"金融企业呆账核销管理办法解读",

 "industry":"金融",

 "output_format":[
   "HTML",
   "WORD"
 ],

 "compare_version":true

}

```

---

## 返回

```json id="create_task_res"

{
 "task_id":"TASK_001",

 "status":"CREATED"

}

```

---

# 4.2 查询任务详情

## API

```http
GET /api/tasks/{task_id}

```

---

## 返回

```json id="task_detail"

{
 "task_id":"TASK_001",

 "status":"PROCESSING",

 "current_step":"S4",

 "progress":65

}

```

---

# 4.3 查询任务流程状态

## API

```http
GET /api/tasks/{task_id}/workflow

```

---

## 返回

```json id="workflow_status"

{

"S1":{
 "status":"SUCCESS"
},

"S2":{
 "status":"SUCCESS"
},

"S3":{
 "status":"SUCCESS"
},

"S4":{
 "status":"RUNNING",
 "progress":65
}

}

```

---

# 4.4 取消任务

## API

```http
POST /api/tasks/{task_id}/cancel

```

---

返回：

```json id="cancel"

{
 "status":"CANCELLED"
}

```

---

# 5. 文件管理接口

---

# 5.1 上传法规文件

## API

```http
POST /api/documents/upload

```

---

## 请求

multipart/form-data

参数：

|字段|说明|
|-|-|
|file|文件|
|document_type|类型|

---

## 返回

```json id="upload"

{
 "document_id":"DOC001",

 "file_name":"xxx.pdf",

 "parse_status":"PENDING"

}

```

---

# 5.2 查询文件状态

## API

```http
GET /api/documents/{document_id}

```

---

返回：

```json id="document_status"

{
 "parse_status":"COMPLETED",

 "ocr_confidence":0.98

}

```

---

# 6. Workflow接口

---

# 6.1 获取流程节点

## API

```http
GET /api/tasks/{task_id}/steps

```

---

返回：

```json id="steps"

[
 {
  "step":"S1",
  "status":"SUCCESS"
 },

 {
  "step":"S4",
  "status":"RUNNING"
 }
]

```

---

# 6.2 重跑指定节点

用于：

- S4失败；
- S5重新比较。

---

## API

```http
POST /api/tasks/{task_id}/steps/{step_id}/retry

```

---

请求：

```json id="retry"

{
 "reason":"重新生成解读"

}

```

---

返回：

```json id="retry_res"

{
 "step":"S4",

 "status":"RUNNING"

}

```

---

# 7. 法规信息接口

---

# 7.1 获取法规详情

## API

```http
GET /api/regulations/{regulation_id}

```

---

返回：

```json id="regulation"

{

"title":"",

"issuer":"",

"publish_date":"",

"effective_date":""

}

```

---

# 7.2 获取法规目录

## API

```http
GET /api/regulations/{regulation_id}/sections

```

---

返回：

```json id="sections"

[
 {
  "section_id":"",
  "title":"第一章 总则"
 }
]

```

---

# 8. 条款接口

---

# 8.1 获取条款列表

## API

```http
GET /api/regulations/{regulation_id}/articles

```

---

返回：

```json id="articles"

[
{
 "article_id":"ART001",

 "article_no":"第一条"

}

]

```

---

# 8.2 获取条款详情

## API

```http
GET /api/articles/{article_id}

```

---

返回：

```json id="article"

{

"article_no":"第十四条",

"original_text":"",

"interpretation_id":""

}

```

---

# 8.3 获取条款关联规则

## API

```http
GET /api/articles/{article_id}/requirements

```

---

返回：

```json id="requirements"

[
{
"requirement_id":"",
"rule_type":"OBLIGATION"
}

]

```

---

# 9. 外规解读接口

---

# 9.1 获取整体解读

## API

```http
GET /api/regulations/{regulation_id}/interpretation

```

---

返回：

```json id="interpretation"

{

"background":"",

"purpose":"",

"positioning":"",

"core_requirements":[]

}

```

---

# 9.2 获取逐条解读

## API

```http
GET /api/articles/{article_id}/interpretation

```

---

返回：

```json id="article_interpretation"

{

"article_id":"",

"original_text":"",

"interpretation":"",

"evidence_ids":[]

}

```

---

# 10. Evidence接口

---

# 10.1 获取证据链

## API

```http
GET /api/evidence/{evidence_id}

```

---

返回：

```json id="evidence"

{

"source_text":"",

"page":14,

"article_id":""

}

```

---

# 10.2 获取结论证据

## API

```http
GET /api/interpretations/{id}/evidence

```

---

返回：

```json id="interpretation_evidence"

[
{
"evidence_id":"",
"source_text":""
}
]

```

---

# 11. 新旧规比较接口

---

# 11.1 获取版本比较结果

## API

```http
GET /api/regulations/{regulation_id}/changes

```

---

返回：

```json id="changes"

[
{
"change_id":"",
"change_type":"TIME_CHANGED"

}

]

```

---

# 11.2 获取变化详情

## API

```http
GET /api/changes/{change_id}

```

---

返回：

```json id="change"

{

"old_text":"",

"new_text":"",

"type":"",

"evidence_ids":[]

}

```

---

# 12. QC接口

---

# 12.1 获取QC结果

## API

```http
GET /api/tasks/{task_id}/qc

```

---

返回：

```json id="qc"

{

"total":1200,

"pass":1195,

"warning":5,

"blocker":0

}

```

---

# 12.2 获取问题详情

## API

```http
GET /api/qc/{qc_id}

```

---

返回：

```json id="qc_detail"

{

"type":"NUMERIC_CHECK",

"severity":"ERROR",

"message":""

}

```

---

# 13. 报告生成接口

---

# 13.1 生成Word报告

## API

```http
POST /api/reports/word

```

---

请求：

```json id="word_generate"

{

"regulation_id":"",

"template":"standard"

}

```

---

返回：

```json id="word_res"

{

"file_id":"",

"status":"GENERATING"

}

```

---

# 13.2 下载报告

## API

```http
GET /api/files/{file_id}

```

---

# 14. HTML页面数据接口

---

# 14.1 获取页面数据包

## API

```http
GET /api/render/{regulation_id}

```

---

返回：

```json id="render_data"

{

"sections":[],

"navigation":{},

"articles":[],

"evidence":[]

}

```

---

# 14.2 获取导航关系

## API

```http
GET /api/render/{regulation_id}/navigation

```

---

返回：

```json id="navigation"

{

"article_id":"",

"next_article_id":"",

"previous_article_id":""

}

```

---

# 15. 人工审核接口

---

# 15.1 获取待审核任务

## API

```http
GET /api/reviews/pending

```

---

# 15.2 提交审核结果

## API

```http
POST /api/reviews/{review_id}

```

---

请求：

```json id="review"

{

"action":"APPROVE",

"comment":""

}

```

---

# 15.3 锁定内容

## API

```http
POST /api/interpretations/{id}/lock

```

---

返回：

```json id="lock"

{

"human_lock":true

}

```

---

# 16. 管理接口

---

# 16.1 Prompt管理

```http
GET /api/prompts

```

---

# 16.2 Skill管理

```http
GET /api/skills

```

---

# 16.3 模型配置

```http
GET /api/models

```

---

# 17. API权限设计

角色：

---

## Admin

权限：

全部。

---

## Reviewer

权限：

- 审核；
- 修改；
- 发布。

---

## User

权限：

- 上传；
- 查看。

---

# 18. API异常处理

统一错误码：

|错误码|说明|
|-|-|
|400|参数错误|
|401|未授权|
|403|权限不足|
|404|对象不存在|
|500|系统错误|
|AI001|模型失败|
|DATA001|数据异常|
|QC001|质量阻断|

---

# 19. API开发注意事项

---

## 19.1 长任务必须异步

禁止：

上传文件后等待HTTP返回完整结果。

---

正确：

```text
POST任务

↓

task_id

↓

GET状态

```

---

## 19.2 所有AI输出必须保存

API返回结果：

同时写数据库。

---

## 19.3 前端禁止直接调用AI服务

架构：

```text
Frontend

↓

Backend API

↓

AI Service

```

---

## 19.4 API必须支持版本

例如：

```text
/api/v1/tasks

/api/v2/tasks

```

---

# 20. API验收标准

完成后应支持：

## 用户流程

上传法规

↓

创建任务

↓

查看进度

↓

查看解读

↓

下载Word。

---

## 开发流程

前后端可独立开发。

---

## AI流程

Skill可独立调用。

---

## 运维

可追踪：

- 请求；
- 任务；
- 错误；
- 输出。

---

# 21. 下一步

完成 API Specification 后，外规解读 Agent 已具备：

- 产品设计；
- 页面设计；
- 数据库设计；
- API设计；
- Agent架构。

下一阶段建议进入：

# 《外规解读 Agent Prompt Library Specification v1.0》

重点整理：

- S1-S6正式Prompt；
- System Prompt；
- User Prompt模板；
- Few-shot案例；
- 错误案例；
- 参数配置；
- 模型调用策略。

该文档将决定AI能力如何真正落地。