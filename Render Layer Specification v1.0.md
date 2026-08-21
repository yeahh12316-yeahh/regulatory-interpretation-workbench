# Render Layer Specification v1.0

---

# 1. 模块定位

## 1.1 模块名称

**展示渲染层（Render Layer）**

英文：

`Rendering & Presentation Layer`

---

# 1.2 核心目标

Render Layer负责将已经通过 QC 校验的结构化监管知识转换为最终用户可使用的展示结果：

包括：

- HTML交互式外规解读页面；
- Word外规解读报告；
- PDF（可选）；
- API输出。

---

# 1.3 核心定位

Render Layer：

> 只负责展示，不负责理解。

---

## Render Layer可以做：

- 页面布局；
- 数据展示；
- 页面跳转；
- 文档排版；
- 目录生成；
- 高亮展示；
- 数据格式转换。

---

## Render Layer禁止做：

- 重新总结法规；
- 修改解读内容；
- 新增监管观点；
- 判断监管趋势；
- 修改Requirement；
- 修改Evidence关系。

---

# 2. Render Layer在整体架构中的位置

```text id="render_flow"

Regulation Data Model

        ↓

S6 Content Package

        ↓

QC Engine

        ↓

Render Layer

        ↓

 ┌──────────────┐
 │ HTML Renderer│
 └──────────────┘

 ┌──────────────┐
 │ Word Renderer│
 └──────────────┘

 ┌──────────────┐
 │ API Renderer │
 └──────────────┘

```

---

# 3. Render Layer设计原则

---

# 3.1 单一数据源原则

HTML：

读取：

```text
Content Package
```

Word：

读取：

```text
Content Package
```

禁止：

HTML重新调用LLM。

禁止：

Word重新调用LLM。

---

# 3.2 数据驱动原则

页面结构由：

Object ID

决定。

不是由：

文本搜索。

---

错误：

```text id="bad_router"

寻找“第十四条”

↓

跳转

```

正确：

```text id="good_router"

article_id

↓

Article Object

↓

页面

```

---

# 3.3 内容不可变原则

Render阶段：

只读。

输入：

```text
QC Passed Data

```

输出：

```text
Presentation Result

```

---

# 3.4 前后端分离原则

建议：

Backend：

负责：

- 数据；
- API；
- 权限；
- 文件生成。

Frontend：

负责：

- 页面；
- 交互；
- 展示。

---

# 4. Render Layer整体架构

```text id="render_arch"

                 Backend


       Content Package API


              ↓


        Render Engine


       ↙          ↓          ↘


 HTML Renderer  Word Renderer  API Renderer


       ↓          ↓


 Web页面       文档文件


```

---

# 5. 输入对象

Render Layer输入：

---

## 5.1 Content Package

来自 S6。

包含：

- 页面章节；
- 条款关系；
- Requirement；
- Evidence；
- Change。

---

## 5.2 QC Result

必须满足：

```text
BLOCKER = 0

ERROR = 0

```

---

输入：

```json id="render_input"

{
 "content_package": {},

 "qc_result": {},

 "template_config": {},

 "user_permission": {}

}

```

---

# 6. 输出对象

---

# 6.1 HTML Output Object

```json id="html_output"

{
 "page_id":"",

 "regulation_id":"",

 "route":"",

 "sections":[],

 "navigation":{},

 "status":""

}

```

---

# 6.2 Word Output Object

```json id="word_output"

{
 "file_id":"",

 "template_id":"",

 "regulation_id":"",

 "generation_time":"",

 "version":""

}

```

---

# 7. HTML Renderer设计

---

# 7.1 页面目标

HTML页面不是普通报告网页。

定位：

> 金融行业外规智能阅读平台。

---

# 7.2 页面结构

推荐：

三栏布局。

```text id="html_layout"

┌───────────────────────┐
│ 法规基本信息            │
└───────────────────────┘


┌────────┬──────────┬──────┐
│目录导航│正文区域   │证据链│
│        │          │      │
└────────┴──────────┴──────┘

```

---

# 8. HTML页面模块设计

---

# 8.1 法规首页

展示：

- 法规名称；
- 发文机构；
- 文号；
- 发布时间；
- 实施日期；
- 状态。

数据：

Regulation Object。

---

# 8.2 监管速览页

展示：

来源：

S4 Executive Summary。

包括：

- 出台背景；
- 目的；
- 定位；
- 核心内容。

---

# 8.3 核心要求页

展示：

Requirement聚类。

例如：

```text id="core_requirement"

制度要求

↓

程序要求

↓

证据要求

↓

报送要求

↓

审计要求

```

---

# 8.4 条款解读页

核心页面。

结构：

```text id="article_page"

第十四条


【外规原文】

↓↓↓

【外规解读】

↓↓↓

【监管要求】

↓↓↓

【关联条款】

↓↓↓

【证据来源】

```

---

# 8.5 新旧规比较页

结构：

```text id="change_page"

旧版本

↓

新版本

↓

差异高亮

↓

变化类型

↓

证据

```

---

# 9. HTML路由设计

这是平台稳定性的核心。

---

## 9.1 禁止

不要：

```text id="wrong_url"

/article?id=第十四条

```

---

## 9.2 推荐

使用对象ID。

---

法规：

```text
/regulation/{regulation_id}
```

---

章节：

```text
/regulation/{regulation_id}/section/{section_id}
```

---

条款：

```text
/regulation/{regulation_id}/article/{article_id}
```

---

Requirement：

```text
/regulation/{regulation_id}/requirement/{requirement_id}
```

---

Evidence：

```text
/regulation/{regulation_id}/evidence/{evidence_id}
```

---

Change：

```text
/regulation/{regulation_id}/change/{change_id}
```

---

# 10. 页面跳转机制

---

## 10.1 条款跳转

用户点击：

> 第十四条

系统：

```text id="jump_flow"

article_id

↓

Article API

↓

Article Detail Page

```

---

## 10.2 Requirement跳转

点击：

> 已核销资产管理要求

流程：

```text id="req_jump"

requirement_id

↓

Requirement API

↓

Article

↓

Evidence

```

---

## 10.3 Evidence跳转

点击：

> 查看原文

流程：

```text id="evidence_jump"

evidence_id

↓

Evidence Object

↓

Source Document

↓

原文位置

```

---

# 11. 页面状态管理

避免：

页面刷新后丢失位置。

---

保存：

```json id="page_state"

{
 "regulation_id":"",

 "article_id":"",

 "scroll_position":1200,

 "from_page":"requirement"

}

```

---

# 12. HTML搜索设计

支持：

---

## 法规搜索

字段：

- 名称；
- 文号；
- 发文机构。

---

## 条款搜索

字段：

- Article.original_text。

---

## 监管要求搜索

字段：

- subject；
- action；
- rule_type；
- threshold。

---

## 解读搜索

字段：

- Interpretation。

---

# 13. Word Renderer设计

---

# 13.1 输出目标

生成：

正式外规解读报告。

适用于：

- 内部分享；
- 管理层阅读；
- 项目交付。

---

# 13.2 Word结构

统一模板：

```
封面

一、法规概览

二、出台背景

三、出台目的

四、法规定位

五、适用范围

六、整体监管框架

七、核心监管要求

八、关键数字要求

九、新旧规比较

十、逐条解读

十一、参考来源

```

---

# 14. Word生成规则

---

## 14.1 不允许重新生成文本

Word Renderer：

读取：

```text
ReportData

```

---

## 14.2 表格自动生成

例如：

监管数字：

|数字|事项|条款|
|-|-|-|

---

版本变化：

|主题|旧规|新规|变化|
|-|-|-|-|

---

# 15. Word与HTML一致性

---

必须：

同一个：

```text
interpretation_id

change_id

evidence_id

```

对应：

同一个内容。

---

# 15.1 一致性检查

生成：

```json id="hash_check"

{
 "html_hash":"",
 "word_hash":"",
 "consistent":true
}

```

---

# 16. PDF Renderer（可选）

流程：

```text
Word

↓

PDF

```

禁止：

HTML直接转PDF作为正式报告。

原因：

- 排版不可控；
- 字体问题；
- 表格容易错位。

---

# 17. API Renderer设计

支持：

未来：

- 移动端；
- 企业系统；
- 内部门户。

---

API示例：

## 获取法规

```http
GET /api/regulations/{id}

```

---

## 获取条款

```http
GET /api/articles/{article_id}

```

---

## 获取证据

```http
GET /api/evidence/{evidence_id}

```

---

# 18. 权限控制设计

金融机构部署必须考虑权限。

---

权限：

```text id="permission"

管理员

↓

审核人员

↓

普通用户

↓

访客

```

---

# 19. 人工修改支持

Render必须支持：

```text
AI Draft

↓

Human Edited

↓

Published

```

---

如果：

human_lock=true

Render读取：

人工版本。

---

# 20. Render Layer质量控制

---

# QC-R01 路由检查

检查：

所有：

- article_id；
- requirement_id；
- evidence_id。

是否存在。

---

错误：

BLOCKER。

---

# QC-R02 页面完整性检查

检查：

HTML：

是否包含：

- 法规信息；
- 导航；
- 正文；
- 证据。

---

# QC-R03 Word完整性检查

检查：

章节是否完整。

---

# QC-R04 一致性检查

检查：

HTML

=

Word

---

# QC-R05 链接测试

自动点击：

随机：

- 条款；
- Requirement；
- Evidence。

验证：

目标正确。

---

# 21. 开发注意事项

---

## 21.1 不建议先开发页面

错误流程：

```text
设计页面

↓

写静态HTML

↓

补数据

```

容易出现：

- 页面孤立；
- 无法跳转；
- 数据无法维护。

---

正确：

```text
Data Model

↓

API

↓

Renderer

↓

页面

```

---

# 21.2 不使用静态HTML作为核心产品

静态HTML只能：

- Demo；
- 展示。

正式平台必须：

动态读取数据。

---

# 21.3 不让前端保存业务逻辑

前端不负责：

- 判断条款；
- 生成关系；
- 判断版本。

---

# 21.4 支持局部刷新

例如：

修改：

第十四条解读。

只更新：

- Article Page；
- Requirement Page；
- Word对应章节。

---

# 22. Benchmark测试

继续使用：

《金融企业呆账核销管理办法》

---

## Case 1

点击：

第十四条。

验证：

正确跳转。

---

## Case 2

点击：

“2年责任期限”。

验证：

跳转：

Requirement

↓

Article

↓

Evidence。

---

## Case 3

修改：

人工锁定内容。

验证：

Renderer是否读取人工版本。

---

## Case 4

生成：

Word和HTML。

验证：

内容一致。

---

# 23. Render Layer与其他模块边界

|模块|职责|
|-|-|
|S3|规则抽取|
|S4|法规解读|
|S5|版本比较|
|S6|内容组织|
|QC Engine|质量检查|
|Render Layer|展示输出|

---

# 24. Render Layer完成标准

完成后，应实现：

## HTML能力

- 在线阅读；
- 条款跳转；
- 证据回溯；
- 新旧规联动；
- 搜索查询。

---

## Word能力

- 自动生成正式报告；
- 格式统一；
- 内容一致。

---

## 平台能力

- 动态加载；
- 数据驱动；
- 可维护；
- 可扩展；
- 支持人工修改。

---

# 25. 下一步

完成 Render Layer 后，外规解读 Agent 的核心技术链路已经形成：

```text id="final_arch"

输入法规

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

外规解读平台

```

下一阶段建议进入：

# Workflow Orchestrator Specification v1.0

设计：

- Agent任务调度；
- Skill调用顺序；
- 状态管理；
- 失败恢复；
- 断点续跑；
- 单节点重跑；
- 用户操作流程。

这部分会直接决定平台是否“真正能运行”。