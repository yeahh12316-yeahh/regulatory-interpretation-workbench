# S5 新旧规版本比较与变化识别 Skill Specification v1.0

---

# 1. Skill定位

## 1.1 Skill名称

**S5 新旧规版本比较与变化识别**

英文：

`Regulation Version Comparison & Change Analysis`

---

## 1.2 核心目标

S5负责对存在版本关系的金融行业监管文件进行结构化比较，识别新旧版本之间的文本变化、规则变化及监管要求调整，并形成可追溯的新旧规差异分析结果。

S5主要解决：

> 新发布监管文件相比历史版本发生了哪些变化？

包括：

- 新增内容；
- 删除内容；
- 条款调整；
- 表述变化；
- 适用范围变化；
- 流程变化；
- 数字变化；
- 条件变化；
- 例外变化。

最终输出：

> 新旧规差异矩阵。

---

## 1.3 S5不负责内容

S5不负责：

- 判断企业是否受到影响；
- 判断企业是否合规；
- 生成整改建议；
- 设计控制措施；
- 评价监管政策优劣；
- 输出未经证据支持的监管趋势判断。

例如：

不输出：

> 新规全面强化监管要求。

除非该结论经过独立分析并明确标记为 Interpretation。

---

# 2. S5在整体架构中的位置

```text
Current Regulation

        +

Previous Regulation

        +

Version Relation Evidence

        ↓

S5 新旧规版本比较与变化识别

        ↓

Article Mapping

        ↓

Change Object

        ↓

Trend Interpretation（可选）

        ↓

S6 内容编排与证据绑定

        ↓

HTML / Word输出
```

---

# 3. S5核心原则

---

# 3.1 版本关系确认优先原则

S5第一步不是比较文本。

第一步：

> 判断两个法规是否存在真实版本关系。

必须区分：

---

## Direct Previous Version

直接前序版本。

例如：

《XXX办法（2023年修订）》

对应：

《XXX办法（2017年版）》

---

## Historical Version

历史版本。

例如：

2013年版本。

可能存在历史关系，但不一定是直接前序版本。

---

## Related Regulation

相关法规。

例如：

同领域监管规则。

---

三者不得混淆。

---

# 3.2 禁止自动推断版本关系

以下方式禁止：

- 根据法规名称相同判断版本关系；
- 根据发布时间先后判断前后关系；
- 根据文本相似度判断直接修订关系。

必须依据：

- 官方修订说明；
- 废止通知；
- 发布通知；
- 条文说明；
- 法规数据库版本关系。

---

# 3.3 先事实变化，再监管解释

正确流程：

```text
旧版本文本

↓

新版本文本

↓

条款映射

↓

文本差异

↓

变化类型

↓

监管含义解释
```

错误流程：

```text
观察标题

↓

判断监管趋势

↓

寻找支持文本
```

---

# 3.4 事实层与解释层分离

S5输出必须区分：

---

## FACT

事实变化。

例如：

> 第十九条责任认定期限由1年调整为2年。

---

## INTERPRETATION

分析判断。

例如：

> 该调整可能影响金融企业责任认定时间安排。

---

不得将解释写成事实。

---

# 4. 输入对象（Input Schema）

S5输入包括：

- 当前版本法规；
- 对比版本法规；
- 版本关系；
- 条款结构；
- 官方说明材料。

---

## 4.1 Input JSON

```json
{
  "current_regulation": {
    "regulation_id": "",
    "title": "",
    "version": "",
    "effective_date": ""
  },

  "previous_regulation": {
    "regulation_id": "",
    "title": "",
    "version": "",
    "effective_date": ""
  },

  "version_relation": {
    "relation_type": "",
    "evidence_ids": [],
    "confidence": 0
  },

  "current_articles": [],

  "previous_articles": [],

  "official_explanation": []
}
```

---

# 5. Version Relation对象

## 5.1 作用

用于确认：

> 两个法规是否可以进行正式版本比较。

---

## 5.2 Schema

```json
{
  "relation_id": "",

  "source_regulation_id": "",

  "target_regulation_id": "",

  "relation_type": "",

  "evidence_ids": [],

  "confidence": 0,

  "verified": false
}
```

---

## 5.3 relation_type

固定：

```text
DIRECT_PREVIOUS_VERSION

HISTORICAL_VERSION

REVISES

REPLACES

REPEALS

RELATED_RULE

SUPERIOR_RULE

UNKNOWN
```

---

## 5.4 版本关系要求

如果：

```text
relation_type = UNKNOWN
```

则：

S5不得生成正式差异结论。

只能输出：

> 待确认版本关系。

---

# 6. 输出对象（Output Schema）

S5核心输出：

## Change Object

---

# 6.1 Change Schema

```json
{
  "change_id": "",

  "current_article_id": "",

  "previous_article_id": "",

  "change_type": "",

  "change_area": "",

  "current_text": "",

  "previous_text": "",

  "difference_summary": "",

  "interpretation": "",

  "evidence_ids": [],

  "confidence": 0,

  "review_status": ""
}
```

---

# 7. Article Mapping设计

## 7.1 目的

解决：

> 新旧法规条款编号不一致问题。

不能简单：

> 第十四条 vs 第十四条。

---

## 7.2 Mapping Schema

```json
{
  "mapping_id": "",

  "current_article_id": "",

  "previous_article_id": "",

  "mapping_type": "",

  "similarity_score": 0,

  "mapping_basis": [],

  "confidence": 0
}
```

---

## 7.3 Mapping Type

固定：

```text
DIRECT

MERGED

SPLIT

MOVED

NEW

REMOVED

UNCERTAIN
```

---

# 8. Change Type标准

---

## 8.1 WORDING_CHANGED

文本表述变化。

示例：

旧：

> 应及时处理。

新：

> 应当及时处理。

若监管含义未发生变化：

标记：

```text
WORDING_CHANGED
```

---

## 8.2 ADDED

新增内容。

例如：

新规新增：

- 新监管主体；
- 新程序要求；
- 新报告要求。

---

## 8.3 DELETED

删除内容。

例如：

旧规存在要求，新规删除。

---

## 8.4 REVISED

规则内容调整。

---

## 8.5 CLARIFIED

明确化。

例如：

旧规：

原则性规定。

新规：

增加明确条件。

---

## 8.6 DETAILED

细化。

例如增加：

- 流程；
- 材料；
- 条件；
- 例外。

---

## 8.7 EXPANDED_SCOPE

范围扩大。

包括：

- 适用机构扩大；
- 适用业务扩大；
- 监管对象扩大。

---

## 8.8 NARROWED_SCOPE

范围缩小。

---

## 8.9 TIME_CHANGED

时间调整。

例如：

1年调整为2年。

---

## 8.10 THRESHOLD_CHANGED

阈值调整。

---

## 8.11 AMOUNT_CHANGED

金额调整。

---

## 8.12 RATIO_CHANGED

比例调整。

---

# 9. 收紧/放宽判断规则

## 9.1 默认原则

变化方向默认：

```text
UNKNOWN
```

---

## 9.2 TIGHTENED

只有存在明确规则变化时使用。

例如：

旧：

> 每年检查一次。

新：

> 每季度检查一次。

可以判断：

```text
TIGHTENED
```

---

## 9.3 RELAXED

只有存在明确规则变化时使用。

例如：

旧：

> 必须取得法院证明。

新：

> 特定情况下允许内部证明。

可以判断：

```text
RELAXED
```

---

## 9.4 禁止表达

禁止直接输出：

> 监管明显趋严。

除非经过独立 Trend Interpretation。

---

# 10. Trend Interpretation设计

监管趋势不是Change Object的一部分。

单独保存。

---

## 10.1 Schema

```json
{
  "trend_id": "",

  "statement": "",

  "basis_change_ids": [],

  "fact_class": "INTERPRETATION",

  "confidence": 0,

  "review_status": ""
}
```

---

## 10.2 示例

允许：

> 从适用范围扩大、管理要求细化等变化来看，新规进一步明确了相关监管要求。

不建议：

> 监管进入全面收紧阶段。

---

# 11. S5处理流程

---

## Step 1：版本关系确认

输入：

Version Relation

输出：

```text
Confirmed
/
Uncertain
```

---

## Step 2：法规结构解析

读取：

- Regulation；
- Article；
- Paragraph；
- Item。

---

## Step 3：条款映射

建立：

Current Article

↓

Previous Article

---

## Step 4：文本比较

识别：

- 新增；
- 删除；
- 修改；
- 数字变化；
- 条件变化。

---

## Step 5：变化分类

生成：

Change Object。

---

## Step 6：形成差异总结

生成：

- 差异矩阵；
- 变化摘要；
- 必要解释。

---

# 12. 差异矩阵输出

HTML和Word统一格式：

| 对比主题 | 原规则 | 新规则 | 变化类型 | 解读 |
|---|---|---|---|---|

---

示例：

|主题|旧规则|新规则|变化类型|
|-|-|-|-|
|适用范围|银行业机构|金融企业|EXPANDED_SCOPE|
|责任期限|1年|2年|TIME_CHANGED|

---

# 13. S5 System Prompt v1.0

```text
你是金融行业外规版本比较模块。

你的任务是基于已经确认版本关系的两个监管文件，对文本差异进行结构化分析。

你的第一优先级是准确识别文本变化，而不是判断监管趋势。

必须遵守：

1. 仅基于输入的新旧版本进行比较。
2. 所有变化必须绑定原文证据。
3. 区分事实变化和解释判断。
4. 不得因为规则变化直接推断监管趋严或放宽。
5. 不得将历史版本作为直接前序版本。
6. 不得根据法规名称自行判断版本关系。
7. 不得补充法规之外的信息。

输出必须包括：

- 新旧条款；
- 条款映射关系；
- 变化类型；
- 差异说明；
- 必要解释；
- 证据来源。

如果无法确认：
输出UNKNOWN，并要求人工复核。
```

---

# 14. S5质量控制规则

---

# QC-S5-01 版本关系检查

检查：

```text
DIRECT_PREVIOUS_VERSION
```

是否存在有效证据。

无证据：

```text
BLOCKER
```

---

# QC-S5-02 条款映射检查

每个Change必须至少存在：

```text
current_article_id

or

previous_article_id
```

否则：

```text
ERROR
```

---

# QC-S5-03 变化真实性检查

Change描述必须能够定位：

- 新版本文本；
- 旧版本文本。

否则：

```text
BLOCKER
```

---

# QC-S5-04 数字变化检查

涉及：

- 日期；
- 金额；
- 比例；
- 时间；
- 阈值。

必须经过：

Numeric Validator。

---

# QC-S5-05 趋势判断检查

扫描：

```text
趋严

放松

强化监管

监管全面升级

监管明显加强
```

若无充分依据：

```text
WARNING
```

---

# QC-S5-06 版本错误检查

如果：

Historical Version

被标记：

Direct Previous Version

则：

```text
BLOCKER
```

---

# 15. S5页面展示设计

HTML页面：

---

## 左侧

版本选择：

```text
当前版本

↓

历史版本
```

---

## 中间

差异矩阵：

展示：

- 旧条款；
- 新条款；
- 高亮变化；
- 变化类型。

---

## 右侧

证据链：

展示：

```
Change Object

↓

Article Mapping

↓

新旧原文

↓

Evidence
```

---

# 16. 页面跳转设计

禁止：

```text
#article14
```

作为核心跳转。

必须使用：

```text
change_id

article_id

mapping_id
```

---

例如：

```text
/change/CHG_001
```

进入：

变化详情页。

---

# 17. 人工审核机制

以下必须人工确认：

## 17.1 版本关系

包括：

- 是否直接前序版本；
- 是否属于替代关系。

---

## 17.2 收紧/放宽判断

因为涉及监管含义。

---

## 17.3 趋势总结

例如：

- 监管导向；
- 管理趋势。

---

## 17.4 多条款综合判断

例如：

多个新增要求共同形成的变化趋势。

---

# 18. S5 Benchmark测试

测试法规：

《金融企业呆账核销管理办法》

---

## Case 1：适用范围变化

验证：

是否正确识别：

适用主体范围调整。

---

## Case 2：期限变化

验证：

1年 → 2年。

输出：

```text
TIME_CHANGED
```

---

## Case 3：证据要求变化

验证：

外部证据与内部证据要求调整。

---

## Case 4：新增要求

验证：

```text
ADDED
```

---

## Case 5：删除要求

验证：

```text
DELETED
```

---

# 19. S5与其他Skill边界

| 内容 | S3 | S4 | S5 |
|-|-|-|-|
| 原文抽取 | ✅ | ❌ | ❌ |
| 规则识别 | ✅ | ❌ | ❌ |
| 条款解释 | ❌ | ✅ | ❌ |
| 背景分析 | ❌ | ✅ | ❌ |
| 版本比较 | ❌ | ❌ | ✅ |
| 变化识别 | ❌ | ❌ | ✅ |
| 趋势判断 | ❌ | 谨慎 | 谨慎 |
| 整改建议 | ❌ | ❌ | ❌ |

---

# 20. 开发注意事项

---

## 20.1 不允许LLM维护版本关系

版本关系必须来自：

- 法规数据库；
- 官方通知；
- 修订说明。

LLM只消费结果。

---

## 20.2 Change Object必须独立存储

原因：

HTML：

- 差异页面；
- 版本比较；
- Word报告；

均需要复用。

---

## 20.3 不允许重新生成变化描述

Word和HTML必须引用同一个：

```text
change_id
```

避免：

HTML：

> 范围扩大。

Word：

> 监管范围显著扩大。

---

## 20.4 支持人工锁定

人工确认后：

```text
human_lock=true
```

AI重新运行不得覆盖。

---

## 20.5 支持单条重跑

例如：

第20条比较失败。

不得重新跑全部法规。

支持：

```text
retry(change_id)
```

---

# 21. S5完成标准

S5完成后，应能够输出：

## 1. 新旧规差异矩阵

## 2. 条款变化列表

## 3. 数字变化列表

## 4. 新增/删除要求列表

## 5. 变化解释

## 6. 可选监管趋势总结

并满足：

- 所有版本关系可证明；
- 所有变化可追溯；
- 所有数字变化准确；
- 所有趋势判断与事实分离；
- 所有结论具备证据链。

---

# 22. 下一步

进入：

# S6 内容编排与证据绑定 Skill Specification v1.0

S6负责连接：

AI处理结果

↓

平台展示

↓

Word报告

↓

HTML交互页面

重点设计：

- 报告生成；
- HTML数据组织；
- 条款跳转；
- Requirement→Article→Evidence链路；
- Word与HTML一致性；
- 人工修改版本控制。

S6完成后，外规解读Agent六个核心Skill形成闭环。