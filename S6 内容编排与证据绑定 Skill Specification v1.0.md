# S6 内容编排与证据绑定 Skill Specification v1.0

---

# 1. Skill定位

## 1.1 Skill名称

**S6 内容编排与证据绑定**

英文：

`Content Orchestration & Evidence Binding`

---

# 1.2 核心目标

S6负责将前序 Skill 产生的结构化监管知识进行统一组织、关联和输出准备，形成：

- 外规解读报告数据；
- HTML交互页面数据；
- Word报告数据；
- 条款导航关系；
- 证据链关系。

S6解决的问题：

> 如何将已经生成的监管知识转换为可阅读、可追踪、可复用的最终产品。

---

# 1.3 S6定位

S6不是内容生成模块。

S6主要负责：

- 内容组织；
- 数据关联；
- 页面结构生成；
- 输出格式转换；
- 证据关系绑定。

---

# 1.4 S6不负责内容

S6禁止：

- 修改法规事实；
- 修改Requirement；
- 修改Article原文；
- 重新解释法规；
- 新增监管观点；
- 判断监管趋势。

---

# 2. S6在整体架构中的位置

```text id="9k3m2p"

S1 文件解析

        ↓

S2 法规关系识别

        ↓

S3 条款拆解

        ↓

S4 外规解读

        ↓

S5 新旧规比较

        ↓

S6 内容编排与证据绑定

        ↓

QC Engine

        ↓

Render Layer

        ↓

HTML / Word / API输出

```

---

# 3. S6核心原则

---

# 3.1 单一数据源原则

HTML、Word、接口输出必须来源于同一套结构化数据。

禁止：

HTML重新调用模型生成内容。

禁止：

Word重新调用模型总结内容。

正确方式：

```text id="7z3dpa"

Regulation Data Model

        ↓

S6 Content Model

        ↓

HTML Renderer

        ↓

Word Renderer

```

---

# 3.2 不修改事实原则

S6只能读取：

- Regulation；
- Article；
- Requirement；
- Interpretation；
- Change；
- Evidence。

不得修改：

- 原文；
- 条款编号；
- 监管要求；
- 数字字段。

---

# 3.3 全链路可追溯原则

所有最终输出内容必须能够追溯：

```text id="n8k4xa"

用户看到的结论

↓

Interpretation

↓

Requirement

↓

Article

↓

Evidence

↓

原始文件

```

---

# 3.4 ID驱动原则

所有关联必须通过唯一ID。

禁止：

根据文本搜索：

“第十四条”

进行页面跳转。

---

正确：

```text id="d9x5kf"

article_id

requirement_id

interpretation_id

evidence_id

change_id

```

---

# 4. 输入对象（Input Schema）

S6输入：

---

## 4.1 Regulation Object

法规基本信息。

---

## 4.2 Article Object

法规原文。

---

## 4.3 Requirement Object

监管规则。

---

## 4.4 Interpretation Object

解读内容。

---

## 4.5 Change Object

新旧规变化。

---

## 4.6 Evidence Object

证据来源。

---

输入结构：

```json id="m1v5oz"
{
 "regulation": {},

 "articles": [],

 "requirements": [],

 "interpretations": [],

 "changes": [],

 "evidence": []
}
```

---

# 5. 输出对象（Output Schema）

S6输出：

## Content Package Object

---

```json id="8j2q0m"
{
 "content_package_id":"",

 "regulation_id":"",

 "overview": {},

 "chapters": [],

 "article_navigation": [],

 "requirement_navigation": [],

 "evidence_links": [],

 "word_report_data": {},

 "html_page_data": {},

 "content_version": 1
}
```

---

# 6. Content Package设计

## 6.1 作用

作为：

HTML、Word、API

共同消费的数据对象。

---

## 6.2 Schema

```json id="w7n8q1"
{
 "package_id":"",

 "regulation_id":"",

 "title":"",

 "sections":[],

 "navigation":{},

 "references":[],

 "version":1,

 "created_at":""
}
```

---

# 7. HTML页面数据模型

---

# 7.1 页面结构

建议：

```text id="z0c1fj"

法规概览

↓

出台背景

↓

出台目的

↓

法规定位

↓

适用范围

↓

监管框架

↓

核心监管要求

↓

关键数字

↓

新旧规变化

↓

逐条解读

↓

原文证据

```

---

# 7.2 HTML Section Object

```json id="6q5h7b"
{
 "section_id":"",

 "section_type":"",

 "title":"",

 "content":"",

 "related_article_ids":[],

 "related_requirement_ids":[],

 "related_evidence_ids":[]
}
```

---

# 8. Word Report数据模型

S6生成：

Word Renderer所需的数据。

---

## 8.1 Report Data

```json id="k0y4gs"
{
 "cover": {},

 "basic_information": {},

 "executive_summary": {},

 "background": {},

 "purpose": {},

 "positioning": {},

 "scope": {},

 "framework": {},

 "core_requirements": [],

 "numeric_requirements": [],

 "version_changes": [],

 "article_interpretations": [],

 "references": []
}
```

---

# 9. 证据绑定设计

这是S6最核心功能之一。

---

# 9.1 Evidence Chain

所有关键内容建立：

```text id="6y5m9f"

Interpretation

↓

Requirement

↓

Article

↓

Evidence

```

---

# 9.2 Evidence Link Object

```json id="p4n8kx"
{
 "source_id":"",

 "target_type":"",

 "target_id":"",

 "relation_type":"",

 "confidence":0.99
}
```

---

# 9.3 relation_type

固定：

```text id="5u3j5z"

SUPPORTS

DERIVED_FROM

RELATED_TO

COMPARES_WITH

```

---

# 10. 内容编排规则

---

# 10.1 执行摘要生成

来源：

S4 Executive Summary。

禁止重新生成。

---

# 10.2 核心监管要求

来源：

Requirement聚类。

例如：

按照：

- 治理；
- 程序；
- 证据；
- 报送；
- 审计；

分类。

---

# 10.3 条款解读

来源：

Interpretation。

展示：

```text id="v4u9s1"

第X条

↓

外规原文

↓

外规解读

↓

监管要求

↓

证据

```

---

# 10.4 新旧规比较

来源：

Change Object。

展示：

```text id="p5g0xa"

旧规则

↓

新规则

↓

变化类型

↓

证据

```

---

# 11. 页面导航设计

这是平台开发重点。

---

# 11.1 禁止方式

禁止：

```html
<a href="#article14">
```

作为主要业务跳转。

原因：

- 页面刷新丢失状态；
- 多页面无法复用；
- 动态加载困难。

---

# 11.2 推荐方式

采用：

```text id="d8r3y5"

Router

+

Object ID

```

---

示例：

法规：

```text
/regulations/REG001
```

条款：

```text
/regulations/REG001/articles/ART014
```

监管要求：

```text
/regulations/REG001/requirements/REQ014001
```

证据：

```text
/regulations/REG001/evidence/EVI001
```

---

# 12. 条款跳转逻辑

用户点击：

> 第十四条

系统：

读取：

```text id="6m9q2k"

article_id

↓

Article Object

↓

Evidence Object

```

---

不是：

搜索：

“第十四条”。

---

# 13. Word与HTML一致性

---

# 13.1 内容统一原则

HTML：

读取：

```text
Interpretation Object
```

Word：

读取：

```text
Interpretation Object
```

---

不能：

HTML一套生成逻辑。

Word另一套生成逻辑。

---

# 13.2 Content Hash

建议：

每个内容对象保存：

```json id="x4v9pp"
{
 "content_id":"",
 "version":1,
 "hash":"abc123"
}
```

用于：

- 一致性检查；
- 版本管理。

---

# 14. 人工修改机制

---

# 14.1 内容状态

统一：

```text id="r8q0wm"

AI_DRAFT

AUTO_CHECKED

HUMAN_REVIEW_REQUIRED

HUMAN_REVIEWED

HUMAN_LOCKED

```

---

# 14.2 人工锁定

如果：

```text
human_lock=true
```

则：

AI重新运行：

不得覆盖。

---

# 14.3 修改版本

每次修改：

生成：

```text id="g3n7q4"

version +1

```

保存：

- 修改人；
- 修改时间；
- 修改原因；
- 修改前内容；
- 修改后内容。

---

# 15. S6 System Prompt v1.0

```text id="w8c4k1"

你是金融行业外规解读平台的内容编排模块。

你的任务是将已经确认的法规结构化数据组织为最终展示内容。

你不得：

1. 修改法规原文；
2. 修改监管规则；
3. 新增监管要求；
4. 重新解释法规；
5. 修改证据关系。

你的工作包括：

1. 将Interpretation组织为报告章节；
2. 将Article、Requirement、Evidence建立关联；
3. 生成HTML页面结构数据；
4. 生成Word报告结构数据；
5. 建立导航关系。

所有关联必须基于唯一ID。

不得通过文本匹配建立关系。

输出必须保证：

- HTML与Word内容一致；
- 所有关键结论可回溯原文；
- 所有跳转路径可定位目标对象。

```

---

# 16. S6质量控制规则

---

# QC-S6-01 内容一致性检查

检查：

HTML内容

=

Word内容

否则：

ERROR。

---

# QC-S6-02 证据绑定检查

核心解读：

必须存在：

```text id="g2v9dc"

evidence_id

```

否则：

ERROR。

---

# QC-S6-03 导航检查

检查：

```text id="m3f8kj"

article_id

requirement_id

evidence_id

```

是否存在。

不存在：

BLOCKER。

---

# QC-S6-04 原文保护检查

检查：

Article.original_text

是否被修改。

若修改：

BLOCKER。

---

# QC-S6-05 人工锁定检查

如果：

```text
human_lock=true
```

禁止覆盖。

---

# 17. 页面展示设计

---

## 17.1 首页

展示：

- 法规名称；
- 发文机关；
- 发布时间；
- 实施时间；
- 解读状态。

---

## 17.2 解读页面

三栏结构：

```text id="3f7qcx"

左：

目录导航


中：

法规解读内容


右：

证据链

```

---

## 17.3 条款页面

展示：

```text id="w6p2sk"

第十四条

↓

原文

↓

解读

↓

监管要求

↓

关联条款

↓

证据

```

---

# 18. 人工审核机制

以下内容建议人工审核：

---

## 18.1 综合总结

例如：

- 核心监管逻辑；
- 监管趋势。

---

## 18.2 高层摘要

用于：

- 董事会；
- 管理层。

---

## 18.3 页面发布

正式发布前：

QC必须通过。

---

# 19. Benchmark测试

测试：

《金融企业呆账核销管理办法》

---

## Case 1

检查：

Word与HTML内容一致。

---

## Case 2

点击：

第十四条。

验证：

是否跳转正确。

---

## Case 3

点击：

责任期限变化。

验证：

是否跳转：

Change

↓

Article

↓

Evidence。

---

## Case 4

人工修改条款解释。

验证：

AI重新生成是否覆盖。

---

# 20. S6与其他Skill边界

| 内容 | S3 | S4 | S5 | S6 |
|-|-|-|-|-|
|规则抽取|✅|❌|❌|❌|
|法规解释|❌|✅|❌|❌|
|版本比较|❌|❌|✅|❌|
|内容组织|❌|❌|❌|✅|
|页面生成|❌|❌|❌|✅|
|证据绑定|部分|部分|部分|✅|
|整改建议|❌|❌|❌|❌|

---

# 21. 开发注意事项

---

## 21.1 S6不是LLM自由生成页面

禁止：

模型输出完整HTML代码。

正确：

模型输出：

```text
结构化Content Package

↓

前端Renderer

↓

HTML
```

---

## 21.2 Word生成不能重新调用模型

否则：

Word和HTML容易不一致。

---

## 21.3 页面跳转必须基于ID

禁止：

字符串搜索。

---

## 21.4 支持断点

例如：

HTML生成失败。

不得重新执行：

S1-S5。

只重新执行：

Render。

---

## 21.5 支持局部更新

例如：

修改：

第十四条解读。

只更新：

相关：

- Interpretation；
- HTML section；
- Word section。

---

# 22. S6完成标准

S6完成后，应实现：

## 内容层

- 自动形成外规解读报告；
- 自动生成逐条解读；
- 自动绑定证据。

---

## 平台层

- HTML可交互浏览；
- 条款可跳转；
- 证据可回溯；
- 新旧规可联动。

---

## 输出层

生成：

### Word报告

用于：

- 下载；
- 归档；
- 分享。

### HTML页面

用于：

- 在线阅读；
- 查询；
- 跳转；
- 追踪。

---

## 23. 下一步

完成 S1-S6 后，下一阶段进入：

# QC Engine Specification v1.0

重点设计：

- 规则校验；
- LLM Reviewer；
- 数字校验；
- 证据校验；
- 内容风格检查；
- HTML链接检查；
- Word/HTML一致性检查；
- 自动发布门槛。

QC Engine 是保证外规解读 Agent 达到金融机构使用标准的关键模块。