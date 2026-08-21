# QC Engine Specification v1.0

---

# 1. QC Engine定位

## 1.1 模块名称

**质量控制引擎（Quality Control Engine）**

英文：

`Quality Control Engine`

---

# 1.2 核心目标

QC Engine负责对外规解读 Agent 全流程输出结果进行质量检查，确保最终输出满足：

- 事实准确；
- 来源可靠；
- 逻辑完整；
- 表述客观；
- 证据可追溯；
- 页面可访问；
- 输出一致。

---

# 1.3 QC Engine解决的问题

外规解读 Agent 最大风险：

## 内容风险

- 条款理解错误；
- 数字错误；
- 漏掉限制条件；
- 误读法律措辞；
- AI自行补充要求。

---

## 数据风险

- 条款关联错误；
- 证据缺失；
- 版本关系错误；
- 数据对象不一致。

---

## 产品风险

- HTML跳转错误；
- Word与HTML内容不一致；
- 人工修改被覆盖。

---

# 1.4 QC定位

QC不是一个简单的“审核Prompt”。

而是：

```text id="qc_arch"

Rule-based QC

        +

LLM Reviewer

        +

Data Validation

        +

Human Review Workflow

```

共同组成质量控制体系。

---

# 2. QC Engine在整体架构中的位置

```text id="qc_flow"

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

发布 / 人工复核

        ↓

HTML

Word

API

```

---

# 3. QC核心原则

---

# 3.1 原文优先原则

所有监管事实必须能够追溯：

```text id="source_chain"

结论

↓

Interpretation

↓

Requirement

↓

Article

↓

Original Regulation

```

---

# 3.2 程序校验优先原则

能够通过程序判断的问题：

优先使用规则校验。

例如：

- 数字；
- 日期；
- 条款编号；
- ID关系；
- 链接状态。

不要交给LLM判断。

---

# 3.3 高风险问题强制阻断

对于以下问题：

不得自动发布：

- 条款引用错误；
- 数字错误；
- 法律措辞错误；
- 版本关系错误；
- 原文被修改。

---

# 3.4 不追求“全部自动化”

QC目标不是：

> AI完全替代人工。

目标：

> AI自动发现高风险问题，将人工集中在复杂判断事项。

---

# 4. QC整体架构

```text id="qc_layer"

                QC Engine


    ┌─────────────────────┐
    │ Rule-based Validator │
    └─────────────────────┘

              +

    ┌─────────────────────┐
    │ LLM Reviewer        │
    └─────────────────────┘

              +

    ┌─────────────────────┐
    │ Output Validator    │
    └─────────────────────┘

              +

    ┌─────────────────────┐
    │ Human Review Flow   │
    └─────────────────────┘

```

---

# 5. QC输入对象

QC读取：

```json id="qc_input"

{
 "task_id":"",

 "regulation": {},

 "articles":[],

 "requirements":[],

 "interpretations":[],

 "changes":[],

 "evidence":[],

 "content_package":{}
}

```

---

# 6. QC输出对象

## QCResult Schema

```json id="qc_result"

{
 "qc_id":"",

 "task_id":"",

 "target_type":"",

 "target_id":"",

 "qc_type":"",

 "severity":"",

 "status":"",

 "message":"",

 "evidence":{},

 "auto_fixable":false,

 "resolved":false,

 "resolved_by":"",

 "resolved_at":""

}

```

---

# 7. QC状态定义

---

## status

```text id="qc_status"

PASS

WARNING

ERROR

BLOCKER

```

---

# 8. Severity定义

---

## INFO

提示信息。

不影响发布。

---

## WARNING

需要关注。

可发布，但建议检查。

---

## ERROR

存在质量问题。

需要修复后发布。

---

## BLOCKER

阻断发布。

必须解决。

---

# 9. QC分类体系

QC分为：

```text id="qc_type"

A. 来源校验

B. 条款校验

C. 规则校验

D. 解读校验

E. 版本校验

F. 输出校验

G. 页面校验

H. 风格校验

I. 人工审核校验

```

---

# 10. A类：来源校验（Source Validation）

---

# QC-A01 来源完整性检查

## 检查对象

SourceDocument

---

## 检查内容

确认：

- 是否存在原始法规文件；
- 是否存在来源信息；
- 是否记录发文机关；
- 是否记录发布日期。

---

## 规则

缺失：

```text
BLOCKER
```

---

# QC-A02 来源等级检查

检查：

Evidence Authority Level。

---

要求：

监管义务：

必须至少：

```text
Level 1

或

Level 2

```

---

例如：

错误：

> 根据咨询机构报告判断监管要求。

结果：

```text
ERROR
```

---

# QC-A03 原文文件完整性

检查：

- 文件是否完整；
- OCR是否完成；
- 页码是否连续。

---

异常：

```text
ERROR
```

---

# 11. B类：条款校验（Article Validation）

---

# QC-B01 条款完整性检查

检查：

Article数量。

例如：

法规：

100条。

解析：

98条。

结果：

```text
BLOCKER
```

---

# QC-B02 条款顺序检查

检查：

```text
第1条
第2条
第3条
```

是否连续。

---

发现：

```text
第1条
第2条
第4条
```

结果：

```text
ERROR
```

---

# QC-B03 原文完整性检查

检查：

Article.original_text

是否：

- 被修改；
- 被摘要；
- 被截断。

---

结果：

BLOCKER。

---

# 12. C类：规则抽取校验（Requirement Validation）

---

# QC-C01 Modal校验

检查：

原文：

> 应

Requirement：

> obligation

一致。

---

高风险：

原文：

> 可以

输出：

> 应当

结果：

```text
BLOCKER
```

---

# QC-C02 禁止词校验

原文：

出现：

- 不得；
- 禁止；
- 严禁。

Requirement必须包含：

```text
PROHIBITION
```

否则：

ERROR。

---

# QC-C03 条件完整性

原文：

包含：

- 如果；
- 符合；
- 经；
- 满足；
- 条件之一。

Requirement：

必须存在：

condition。

---

否则：

BLOCKER。

---

# QC-C04 例外完整性

原文：

包含：

- 除……外；
- 但是；
- 除非。

必须存在：

exception。

---

否则：

BLOCKER。

---

# 13. D类：数字校验（Numeric Validation）

金融监管中最高优先级。

---

# QC-D01 数字完整性

检查：

原文数字：

↓

结构化数字。

---

范围：

- 日期；
- 年；
- 月；
- 日；
- 金额；
- 比例；
- 数量。

---

缺失：

BLOCKER。

---

# QC-D02 起算点校验

例如：

原文：

> 会计年度终了后6个月内。

不能输出：

> 6个月。

必须包含：

```text
reference_point

会计年度终了

```

---

否则：

ERROR。

---

# QC-D03 单位校验

检查：

数字单位：

- 天；
- 月；
- 年；
- 工作日。

是否一致。

---

# QC-D04 比较符校验

例如：

原文：

> 不低于50%。

结构：

必须：

```
>=50%
```

不能：

```
=50%
```

---

# 14. E类：解读质量校验（Interpretation Validation）

---

# QC-E01 解读新增义务检查

检查：

Interpretation中的要求。

是否存在：

Requirement。

---

不存在：

BLOCKER。

---

# QC-E02 事实/解读分类检查

检查：

FACT内容。

不得出现：

- 体现监管趋势；
- 反映监管导向。

---

否则：

WARNING。

---

# QC-E03 过度解释检查

扫描：

```text
全面

显著

极大

重大

根本

史上最严

```

---

如果：

无官方依据。

结果：

WARNING。

---

# QC-E04 绝对化检查

检查：

例如：

> 必然导致

> 一定会

> 完全解决

默认：

WARNING。

---

# 15. F类：版本比较校验

---

# QC-F01 版本关系校验

检查：

Direct Previous Version。

必须有：

Evidence。

---

无：

BLOCKER。

---

# QC-F02 条款映射校验

Change Object：

必须存在：

- current_article_id；
- previous_article_id。

---

异常：

ERROR。

---

# QC-F03 趋势判断校验

例如：

输出：

> 监管趋严。

检查：

是否有：

- 多项明确变化；
- 官方说明。

否则：

WARNING。

---

# 16. G类：输出一致性校验

---

# QC-G01 Word/HTML一致性

检查：

同一：

```text
interpretation_id

```

内容是否一致。

---

不一致：

ERROR。

---

# QC-G02 Content Hash校验

检查：

HTML：

hash

Word：

hash

---

不一致：

ERROR。

---

# QC-G03 报告完整性

检查：

Word：

是否包含：

- 基本信息；
- 核心要求；
- 条款解读；
- 证据来源。

---

缺失：

ERROR。

---

# 17. H类：HTML页面校验

---

# QC-H01 页面路由检查

检查：

```text
article_id

requirement_id

evidence_id

change_id

```

是否有效。

---

无效：

BLOCKER。

---

# QC-H02 页面跳转测试

自动测试：

点击：

第十四条

是否进入：

ART_014。

---

错误：

BLOCKER。

---

# QC-H03 返回路径检查

检查：

用户：

条款

↓

证据

↓

返回

是否保持位置。

---

# 18. I类：人工审核流程

---

# 18.1 自动通过

条件：

```text
BLOCKER = 0

ERROR = 0

```

---

# 18.2 人工复核

触发：

- WARNING存在；
- 趋势判断；
- 综合总结；
- 收紧/放宽判断。

---

# 18.3 强制人工审核

触发：

- 法规版本不确定；
- OCR错误；
- 法律措辞冲突；
- 重大监管判断。

---

# 19. LLM Reviewer设计

QC不是全部规则。

需要一个Reviewer。

---

## System Prompt

```text id="qc_prompt"

你是金融行业外规解读质量审核模块。

你的任务不是重新解释法规，而是检查AI生成结果是否准确、完整、客观。

重点检查：

1. 是否符合原文；
2. 是否存在新增要求；
3. 是否遗漏条件和例外；
4. 是否存在数字错误；
5. 是否存在过度解释；
6. 是否存在绝对化表达；
7. 是否存在证据不足判断。

审核时必须区分：

FACT

OFFICIAL

INTERPRETATION

不得因为行业经验补充监管要求。

输出：

问题描述

严重等级

依据

修复建议

```

---

# 20. QC页面设计

HTML：

三栏：

```text id="qc_page"

左：

检查项目


中：

问题详情


右：

修复建议+证据

```

---

# 21. QC Dashboard

首页展示：

```text id="qc_dashboard"

总检查项：

1200


通过：

1180


Warning：

15


Error：

5


Blocker：

0

```

---

# 22. Benchmark测试

继续使用：

《金融企业呆账核销管理办法》

---

## Case 1

修改：

“可以”

为：

“应当”

验证：

Modal检查。

---

## Case 2

删除：

“2年”

验证：

数字检查。

---

## Case 3

删除：

“除……外”

验证：

例外检查。

---

## Case 4

修改：

HTML跳转ID。

验证：

Navigation检查。

---

## Case 5

修改Word内容。

验证：

一致性检查。

---

# 23. QC与Skill边界

|模块|职责|
|-|-|
|S1|文件解析|
|S2|法规识别|
|S3|规则抽取|
|S4|法规解读|
|S5|版本比较|
|S6|内容编排|
|QC Engine|质量验证|

---

# 24. 开发注意事项

---

## 24.1 QC不要只依赖LLM

规则问题：

必须程序检查。

例如：

- 数字；
- ID；
- 链接；
- Hash。

---

## 24.2 QC结果必须保存

不能只显示一次。

保存：

```text
qc_id

target_id

result

timestamp

reviewer

```

---

## 24.3 支持重新检查

用户修改内容后：

只重新执行相关QC。

例如：

修改第十四条：

重新检查：

- Interpretation；
- Evidence；
- HTML；
- Word。

---

## 24.4 发布必须经过QC Gate

流程：

```text
生成

↓

QC

↓

人工审核

↓

发布

```

禁止：

生成后直接展示正式版本。

---

# 25. QC Engine完成标准

完成后，应实现：

## 内容质量

- 关键结论有证据；
- 数字准确；
- 条款准确；
- 解释客观。

---

## 数据质量

- ID关系完整；
- 数据一致；
- 版本关系正确。

---

## 产品质量

- HTML跳转正常；
- Word输出一致；
- 修改可追踪。

---

## 发布标准

满足：

```text
BLOCKER = 0

ERROR = 0

关键WARNING已人工确认

```

才允许正式发布。

---

# 26. 下一步

完成 QC Engine 后，进入：

# Render Layer Specification v1.0

重点设计：

- HTML Renderer；
- Word Renderer；
- 前端页面结构；
- 路由设计；
- 数据接口；
- 文件生成流程；
- 用户交互流程。

这一层将直接对应你最终部署的“外规解读平台/网站”。