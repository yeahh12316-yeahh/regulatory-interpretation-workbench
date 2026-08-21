# S3 条款拆解与监管规则抽取 Skill Specification v1.0

## 1. Skill定位

### 1.1 Skill名称

**S3 条款拆解与监管规则抽取**

英文建议：

`Regulatory Article Decomposition & Requirement Extraction`

---

## 1.2 核心目标

S3 负责将法规条款从自然语言文本转换为结构化监管规则对象 `Requirement Object`。

S3只回答：

> **“法规原文写了什么？”**

S3不回答：

> “这意味着什么？”  
> “监管趋势是什么？”  
> “企业应该怎么办？”  
> “这个要求是否合理？”  
> “是否属于重大变化？”

上述内容属于后续 S4、S5 或人工判断范围。

---

## 1.3 S3在整体架构中的位置

```text
Article Object
+
Regulation Metadata
+
必要上下文
        ↓
S3 条款拆解与监管规则抽取
        ↓
Requirement Object(s)
+
Evidence Binding
+
Extraction QC
        ↓
S4 条款逐条解读
```

---

# 2. S3的基本原则

## 2.1 原文优先

不得使用模型常识补充法规没有写明的要求。

例如原文：

> 金融企业应及时核销呆账。

S3只可以提取：

- 主体：金融企业
- 行为：核销
- 对象：呆账
- 时限属性：及时
- 义务类型：义务

不得生成：

> 30日内完成核销。

---

## 2.2 不解释、不评价

原文：

> 应建立呆账核销责任认定和追究制度。

S3不得输出：

> 该条体现监管进一步强化责任追究。

正确方式：

```text
subject = 金融企业
action = 建立
object = 呆账损失责任认定和追究制度
rule_type = OBLIGATION + RESPONSIBILITY
```

---

## 2.3 不改变法律措辞强度

必须严格区分：

```text
应当 / 应
不得
可以
可
原则上
至少
不低于
不超过
除……外
符合……条件的
```

这些词不得在结构化过程中丢失。

---

## 2.4 条件和例外优先保护

如果原文含有：

> 除……外

则 `exception` 原则上必须有值。

如果原文含有：

> 符合以下条件之一

则 `condition` 原则上必须有值。

如果原文含有：

> 经……后

则必须判断其属于：

- 前置条件；
- 程序要求；
- 审批要求；
- 证据要求。

不得直接省略。

---

# 3. 输入对象

建议 S3 每次只处理一个 Article。

不要一次向模型输入整部法规并要求一次性抽取全部 Requirement。

这样有利于：

- 降低漏项；
- 控制上下文；
- 单条失败重跑；
- 保留断点；
- 精确 QC。

---

# 4. Input JSON Schema

```json
{
  "task_id": "TASK_XXX",

  "regulation": {
    "regulation_id": "REG_XXX",
    "title": "金融企业呆账核销管理办法（2017年版）",
    "document_no": "财金〔2017〕90号",
    "issuer": ["财政部"],
    "effective_date": "2017-10-01",
    "status": "EFFECTIVE"
  },

  "article": {
    "article_id": "ART_014",
    "article_no": "第十四条",
    "chapter_title": "已核销资产管理",
    "original_text": "……",
    "article_order": 14
  },

  "context": {
    "previous_article": {
      "article_id": "ART_013",
      "article_no": "第十三条",
      "original_text": "……"
    },

    "next_article": {
      "article_id": "ART_015",
      "article_no": "第十五条",
      "original_text": "……"
    }
  }
}
```

---

# 5. 为什么只给前后一条上下文

S3主要进行条款级抽取，不应获得过多上下文。

否则模型容易：

> 将其他条款的要求误并入当前条款。

默认仅提供：

- 当前条款；
- 前一条；
- 后一条。

只有遇到：

- “前款”
- “上述”
- “本章”
- “按照第X条”
- “符合前条规定”
- 附件引用

等明确跨条款引用时，再由系统按需追加关联条款。

---

# 6. Output JSON Schema

```json
{
  "article_id": "ART_014",

  "article_classification": {
    "article_types": [
      "OBLIGATION",
      "RIGHT",
      "EXCEPTION"
    ],
    "has_requirement": true,
    "has_condition": true,
    "has_exception": true,
    "has_numeric_rule": false
  },

  "requirements": [
    {
      "requirement_id": "REQ_014_001",

      "rule_type": [
        "OBLIGATION"
      ],

      "subject": [
        "金融企业"
      ],

      "modal_expression": "应",

      "action": "加强管理",

      "object": "已核销债权、股权等资产",

      "condition": [],

      "exception": [
        {
          "text": "权利义务已经终结的情形",
          "source_text": "除权利义务已经终结外"
        }
      ],

      "deadline": null,

      "frequency": null,

      "threshold": [],

      "amount": [],

      "ratio": [],

      "evidence_requirement": [],

      "approval_requirement": null,

      "reporting_requirement": null,

      "penalty": null,

      "related_article_ids": [],

      "source_text": "……",

      "source_span": {
        "start": 0,
        "end": 42
      },

      "fact_class": "FACT",

      "confidence": 0.99,

      "needs_human_review": false,

      "review_reason": null
    }
  ],

  "unresolved_references": [],

  "extraction_notes": [],

  "qc_flags": []
}
```

---

# 7. Requirement拆分基本规则

## 7.1 一个独立监管动作原则上形成一个 Requirement

例如：

> 金融企业应建立资产保全制度和尽职追偿制度。

建议拆成两个 Requirement：

### Requirement 1

```text
action = 建立
object = 资产保全制度
```

### Requirement 2

```text
action = 建立
object = 尽职追偿制度
```

原因：

未来用户可能单独搜索：

> “尽职追偿制度”

也可能单独建立证据、标签和关联关系。

---

## 7.2 但不得过度拆解

原文：

> 应建立健全内部控制制度。

不能拆成：

- 建立制度
- 健全制度

这是一个完整的监管动作。

---

# 8. 主体识别规则

## 8.1 明确主体

原文：

> 金融企业应……

输出：

```text
subject = ["金融企业"]
```

---

## 8.2 承接主体

如果上一句：

> 金融企业应建立……

下一句：

> 同时应加强……

则如果语法明确承接，可以沿用：

```text
subject = ["金融企业"]
```

但应增加：

```text
subject_inferred_from_context = true
```

---

## 8.3 不得凭常识补主体

原文没有明确指出主体且无法从上下文确定：

```text
subject = []
needs_human_review = true
```

不得自动填：

> 金融机构 / 金融企业 / 监管机构。

---

# 9. Modal Expression——法律措辞强度

必须单独保存：

```text
modal_expression
```

推荐允许值：

```text
应当
应
必须
不得
禁止
严禁

可以
可
有权

原则上
通常
一般

至少
不得低于
不得超过
不超过

鼓励
支持
引导

其他
```

---

# 10. Modal与Rule Type映射

### 应 / 应当 / 必须

一般：

`OBLIGATION`

### 不得 / 禁止 / 严禁

一般：

`PROHIBITION`

### 可以 / 可 / 有权

一般：

`PERMISSION`

### 鼓励 / 支持 / 引导

不得识别为强制义务。

建议：

`PRINCIPLE` 或 `OTHER`

---

# 11. “及时”如何处理

原文：

> 应及时核销。

不得将：

```text
deadline = 及时
```

直接解释成具体时间。

建议：

```json
{
  "deadline": {
    "type": "QUALITATIVE",
    "original_expression": "及时",
    "value": null,
    "unit": null
  }
}
```

这样未来页面可以明确展示：

> 法规仅规定“及时”，未设置具体期限。

---

# 12. 条件识别

常见条件词：

```text
符合……
在……情况下
当……
若……
如……
经……
满足……
达到……
出现……
发生……
完成……后
```

---

## 12.1 示例

原文：

> 经采取必要措施和实施必要程序后，符合附件规定条件之一的，可以认定为呆账。

应抽取：

```json
{
  "condition": [
    {
      "type": "PROCEDURAL_PRECONDITION",
      "text": "已采取必要措施并实施必要程序"
    },
    {
      "type": "ELIGIBILITY",
      "text": "符合附件规定条件之一"
    }
  ]
}
```

不得简化成：

> 满足条件即可认定。

---

# 13. “之一”的处理

如果原文：

> 符合下列条件之一

必须保存：

```text
condition_logic = OR
```

如果：

> 同时符合下列条件

必须保存：

```text
condition_logic = AND
```

这是非常重要的逻辑字段。

---

# 14. 建议Condition Schema

```json
{
  "condition_group_id": "CG001",
  "logic": "AND",
  "conditions": [
    {
      "condition_id": "C001",
      "text": "……",
      "source_text": "……"
    }
  ]
}
```

支持嵌套：

```text
A AND (B OR C)
```

金融法规里经常出现这种逻辑。

---

# 15. 例外识别

重点词：

```text
除……外
但……
但是……
除非……
不包括……
以下情形除外
有下列情形之一的除外
```

---

## 15.1 示例

> 除权利义务已经终结外，金融企业仍享有……

必须拆出：

```json
{
  "exception": [
    {
      "text": "权利义务已经终结",
      "source_text": "除权利义务已经终结外"
    }
  ]
}
```

不能只抽：

> 金融企业仍享有相关权利。

否则法律含义已经发生变化。

---

# 16. “但书”处理

例如：

> 可以开展相关业务，但法律法规另有规定的除外。

Requirement必须同时包含：

```text
PERMISSION
+
EXCEPTION
```

而不是生成两个互不关联的 Requirement。

---

# 17. 数字提取规则

所有以下数据必须进入独立结构：

- 金额
- 比例
- 天
- 月
- 年
- 次
- 工作日
- 自然日
- 截止日期
- 起算点
- 上限
- 下限
- 区间

---

# 18. 数字对象

```json
{
  "value": 2,
  "unit": "year",
  "operator": "<=",
  "reference_point": "呆账核销日",
  "original_expression": "呆账核销后2年内"
}
```

---

# 19. Operator标准

```text
=
>
>=
<
<=
BETWEEN
APPROX
UNKNOWN
```

语言映射：

```text
不少于 → >=
至少 → >=
超过 → >
高于 → >
不超过 → <=
以内 → <=
低于 → <
不足 → <
```

---

# 20. “以上/以下”问题

中文法规中“以上、以下、以内、届满”存在具体法律含义。

S3原则上：

> 保留原文表达 + 标准化 operator。

但不要自行判断是否包含本数以外的复杂法律解释。

建议同时保留：

```text
original_expression
normalized_operator
```

---

# 21. 起算点必须提取

原文：

> 会计年度终了后6个月内。

不能只存：

```text
6个月
```

还必须保存：

```text
reference_point = 会计年度终了
```

否则数字失去意义。

---

# 22. 频率提取

例如：

> 每年开展一次。

```json
{
  "frequency": {
    "count": 1,
    "period": "year",
    "minimum": true,
    "original_expression": "每年至少开展一次"
  }
}
```

---

# 23. 报送要求

建议独立结构：

```json
{
  "reporting_requirement": {
    "reporter": ["金融企业"],
    "recipient": ["同级财政部门"],
    "content": [
      "上年度呆账核销情况",
      "专项审计报告"
    ],
    "deadline": {
      "value": 6,
      "unit": "month",
      "reference_point": "会计年度终了"
    }
  }
}
```

---

# 24. 审批要求

例如：

> 经有关部门集体审议后，由有权人审批。

建议：

```json
{
  "approval_requirement": {
    "review_required": true,
    "review_body": [
      "核销处置部门",
      "信贷管理部门",
      "财务会计部门",
      "法律合规部门",
      "内控部门"
    ],
    "decision_maker": "有权人",
    "sequence": [
      "集体审议",
      "有权人审批"
    ]
  }
}
```

如果法规没有明确部门名称：

> 不得自行补充。

---

# 25. 证据要求

例如法规明确要求：

- 法院裁定；
- 仲裁材料；
- 清收报告；
- 法律意见书。

必须形成：

```text
rule_type = EVIDENCE
```

并结构化：

```json
{
  "evidence_requirement": [
    {
      "evidence_name": "清收报告",
      "required": true,
      "condition": "无法取得相关外部证据的特定情形"
    }
  ]
}
```

---

# 26. “包括但不限于”的处理

例如：

> 包括但不限于贷款、债券、投资……

不得将列举项理解为封闭范围。

需要：

```text
list_type = NON_EXHAUSTIVE
```

如果：

> 包括以下三类

且上下文表明封闭列表：

```text
list_type = EXHAUSTIVE
```

不确定：

```text
UNKNOWN
```

---

# 27. “等”字处理

原文出现：

> 贷款、债券等金融资产

不得将列表自动扩写。

只保留法规明确列举项：

```text
贷款
债券
```

同时：

```text
list_open_ended = true
```

---

# 28. “原则上”的处理

原文：

> 原则上不得……

必须保留：

```text
modal_expression = 原则上不得
```

不能直接输出：

```text
PROHIBITION = absolute
```

建议增加：

```text
qualification = PRINCIPLE_BASED
```

---

# 29. “可以”的处理

法规：

> 可以认定为呆账。

S3不得改成：

> 应认定为呆账。

这是高风险错误。

建议 QC 强制比较：

```text
原文 modal
vs
结构化 modal
```

---

# 30. “应”和“应当”的处理

两者均可归入：

`OBLIGATION`

但必须保存原文：

```text
modal_expression
```

这样后续证据展示不损失原文精度。

---

# 31. 多层条件逻辑

假设：

> 对符合A，且B或者C之一的资产，可以核销。

应该表示：

```text
A AND (B OR C)
```

不能展开成：

```text
A
B
C
```

否则会破坏核销准入逻辑。

---

# 32. 跨条款引用

原文：

> 按照本办法第十六条规定处理。

S3输出：

```json
{
  "related_article_ids": ["ART_016"],
  "relation_type": "CITES"
}
```

如果 Article ID 还无法解析：

```json
{
  "unresolved_references": [
    {
      "reference_text": "本办法第十六条",
      "expected_article_no": "第十六条"
    }
  ]
}
```

后续由程序解析。

---

# 33. “前款”处理

不得让模型猜。

系统应该根据条款结构提供：

```text
paragraph_id
```

例如：

```text
ART_014_P01
ART_014_P02
```

“前款”应该链接：

```text
ART_014_P01
```

因此 Article 后续建议再支持：

> Paragraph Object

但 MVP 可以先作为 Article 内部字段实现。

---

# 34. Paragraph Schema 建议

```json
{
  "paragraph_id": "ART_014_P02",
  "article_id": "ART_014",
  "paragraph_order": 2,
  "original_text": ""
}
```

这会明显提高：

- “前款”
- “前项”
- “前述”
- “本款”

等引用的准确性。

---

# 35. 项、目结构

法规经常：

```text
（一）
（二）
（三）
```

甚至：

```text
1.
2.
3.
```

建议后续解析为：

```text
Article
↓
Paragraph
↓
Item
```

否则逐条解读时会失去结构。

---

# 36. MVP建议

第一阶段可以采用：

```text
Article
+
structured_segments[]
```

例如：

```json
{
  "segments": [
    {
      "segment_id": "ART_005_ITEM_01",
      "label": "（一）",
      "text": ""
    }
  ]
}
```

不必一开始建设复杂法律文书树。

---

# 37. S3 System Prompt v1.0

你可以把下面内容作为 S3 的基础 System Prompt。

---

## System Prompt

你是“金融行业外规条款拆解与监管规则抽取模块”。

你的唯一任务是依据提供的监管外规原文，将法规条款拆解为结构化监管规则。

你不是法规解读模块，不得评价监管政策，不得分析监管趋势，不得提出企业整改建议，不得根据行业经验补充法规未明确规定的要求。

### 一、基本要求

1. 以外规原文为最高事实依据。
2. 严格保留法规原意，不得扩大、缩小或改变义务强度。
3. 必须准确识别“应当、应、必须、不得、禁止、可以、可、有权、原则上、至少、不低于、不超过、除……外、但、符合……条件”等限定词。
4. 条件、例外、时限、金额、比例、频率和起算点不得因摘要而丢失。
5. 不得根据常识补充原文不存在的监管主体、要求、时限、阈值、处罚或程序。
6. 如果无法确认，应输出未知或进入人工复核，不得猜测。
7. 一个独立监管动作原则上生成一个 Requirement，但不得对同一完整监管动作进行无意义拆分。
8. 所有 Requirement 必须绑定对应的原始条款文本。
9. 输出仅允许采用指定 JSON Schema，不输出说明性文章。

### 二、法规规则识别

你需要识别以下规则类型：

- DEFINITION
- SCOPE
- PRINCIPLE
- OBLIGATION
- PROHIBITION
- PERMISSION
- CONDITION
- EXCEPTION
- PROCEDURE
- APPROVAL
- EVIDENCE
- TIME_LIMIT
- FREQUENCY
- THRESHOLD
- AMOUNT
- RATIO
- REPORTING
- DISCLOSURE
- GOVERNANCE
- AUDIT
- RESPONSIBILITY
- PENALTY
- TRANSITION
- RIGHT
- TERMINATION
- OTHER

不得创建新的规则类型。

### 三、数值规则

涉及日期、天数、工作日、月、年、金额、比例、次数等信息时：

- 保留法规原始表达；
- 同时进行结构化；
- 识别数值；
- 识别单位；
- 识别比较运算符；
- 识别起算点；
- 不得将原则性时间要求转换为具体数字。

例如“及时”只能标记为定性时限，不得转换为具体天数。

### 四、条件和例外

必须优先识别：

- 若
- 如
- 当
- 在……情况下
- 符合
- 经
- 只有
- 同时满足
- 满足之一
- 除……外
- 但
- 但是
- 除非

如果条件之间存在 AND / OR 逻辑，应保留其逻辑关系。

不得把“符合A或B之一”改写为同时满足A和B。

### 五、法律措辞

“应、应当、必须”通常为义务。

“不得、禁止、严禁”通常为禁止。

“可以、可、有权”通常为许可或授权。

“鼓励、支持、引导”不得默认转换为强制义务。

必须保留原始 modal_expression。

### 六、信息不足

出现以下情况时设置 needs_human_review=true：

- 主体无法确定；
- 条件逻辑存在歧义；
- 引用其他条款但未提供；
- OCR疑似错误；
- 数值表达存在歧义；
- 无法判断规则类型；
- 上下文不足；
- 原文存在明显内部冲突。

必须说明 review_reason。

### 七、禁止事项

禁止：

- 添加原文没有的监管要求；
- 添加企业管理建议；
- 使用形容词评价监管力度；
- 对规则作价值判断；
- 推测监管意图；
- 生成“监管趋严、监管强化”等结论；
- 使用第三方资料覆盖法规原文。

最终仅输出符合指定 Schema 的 JSON。

---

# 38. User Prompt Template

系统每处理一条 Article，可以向模型发送：

```text
请依据 System Prompt，对以下外规条款进行结构化监管规则抽取。

【法规基本信息】
法规名称：{{regulation.title}}
文号：{{regulation.document_no}}
发文机构：{{regulation.issuer}}

【当前条款】
条款ID：{{article.article_id}}
条款编号：{{article.article_no}}
章节：{{article.chapter_title}}

条款原文：
{{article.original_text}}

【必要上下文】
前一条：
{{previous_article.original_text}}

后一条：
{{next_article.original_text}}

请仅输出指定 JSON。
```

---

# 39. S3不建议使用的Prompt写法

不要：

> 请你作为资深金融监管专家，对以下法规进行深入分析并提炼监管重点。

这个 Prompt 已经把任务推向 S4。

也不要：

> 请结合行业实践理解条文背后的监管意图。

这会增加幻觉。

S3需要刻意“保守”。

---

# 40. Confidence规则

建议模型输出置信度，但置信度不能完全由模型自由决定。

可以结合程序规则。

### 0.95—1.00

原文明确：

```text
金融企业应……
不得……
应在6个月内……
```

### 0.85—0.94

存在一定语法承接，但逻辑明确。

### 0.70—0.84

需要跨句、跨款理解。

### <0.70

应进入人工复核。

---

# 41. 自动人工复核触发条件

无论模型 confidence 多高，只要出现以下情况，也强制 Review：

```text
原则上
一般情况下
除特殊情形外
监管机构认可的其他情形
必要时
适当
合理
及时
重大
明显
充分
有关规定
另有规定
```

原因是：

这些属于相对开放或判断型概念。

S3可提取原文，但后续解释需要谨慎。

---

# 42. Rule-based QC 01：Modal Check

程序搜索 Article 中：

```text
应
应当
不得
可以
可
原则上
必须
至少
不低于
不超过
```

与 Requirement 中：

```text
modal_expression
```

逐一比对。

如果原文有：

> 不得

但所有 Requirement 均没有 PROHIBITION：

```text
BLOCKER
```

---

# 43. QC 02：Numeric Check

正则提取原文：

```text
数字
百分数
日期
天
工作日
月
年
元
万元
亿元
次数
```

与结构化字段比较。

原文：

> 2年内

结果缺少 2：

```text
BLOCKER
```

---

# 44. QC 03：Exception Check

原文出现：

```text
除
但
但是
除非
除外
```

结果：

```text
exception = []
```

至少生成：

```text
WARNING
```

如果明显改变监管义务：

```text
BLOCKER
```

---

# 45. QC 04：Condition Check

原文：

> 符合……条件之一

而：

```text
condition = []
```

直接：

```text
ERROR / BLOCKER
```

---

# 46. QC 05：Source Binding

每个 Requirement：

```text
source_text
```

必须存在于：

```text
article.original_text
```

否则：

> BLOCKER

防止模型生成不存在的原句。

---

# 47. QC 06：Hallucination Check

Requirement 中的：

```text
subject
action
object
condition
exception
deadline
```

如果关键内容无法在 Article 或明确上下文中定位：

> `HUMAN_REVIEW_REQUIRED`

对于数字：

> 直接 ERROR。

---

# 48. QC 07：Over-splitting Check

如果一条20字左右的简单义务被拆成5—10个 Requirement：

提示：

> 疑似过度拆解。

由 LLM Reviewer 复核。

---

# 49. QC 08：Under-splitting Check

如果 Article 含：

> 应A，并应B，同时不得C。

但只有一个 Requirement：

> 疑似拆分不足。

---

# 50. Benchmark Case 01：明确义务

测试原文：

> 金融企业应建立健全呆账核销管理制度。

期望：

```json
{
  "rule_type": ["OBLIGATION"],
  "subject": ["金融企业"],
  "modal_expression": "应",
  "action": "建立健全",
  "object": "呆账核销管理制度"
}
```

---

# 51. Benchmark Case 02：条件 + 许可

原文：

> 经采取必要措施和实施必要程序后，符合规定条件之一的，可以认定为呆账。

期望：

```text
rule_type:
PERMISSION
CONDITION

condition:
采取必要措施
实施必要程序
符合规定条件之一

modal:
可以

action:
认定

object:
呆账
```

---

# 52. Benchmark Case 03：例外

原文：

> 除权利义务已经终结外，金融企业对已核销债权仍享有合法权益。

必须包含：

```text
exception:
权利义务已经终结
```

遗漏即不通过。

---

# 53. Benchmark Case 04：数字 + 起算点

原文：

> 应在每个会计年度终了后6个月内报送。

必须输出：

```text
value = 6
unit = month
reference_point = 会计年度终了
operator = <=
```

---

# 54. Benchmark Case 05：责任认定

原文：

> 对确系主观原因形成损失的，应在呆账核销后2年内完成责任认定和责任追究。

应拆为：

### 条件

```text
确系主观原因形成损失
```

### 时限

```text
2年内
```

### 起算点

```text
呆账核销
```

### 行为

可以形成两个 Requirement：

```text
完成责任认定
完成责任追究
```

两者共享相同条件和时限。

---

# 55. 错误示例 01：扩大义务

原文：

> 可以认定为呆账。

错误：

```text
金融企业应认定为呆账。
```

问题：

> PERMISSION → OBLIGATION

Severity：

`BLOCKER`

---

# 56. 错误示例 02：遗漏条件

原文：

> 符合A、B条件的，可以……

输出：

> 可以……

问题：

> 监管条件丢失。

Severity：

`BLOCKER`

---

# 57. 错误示例 03：数字没有语境

原文：

> 年度终了后6个月内报送。

输出：

```text
6个月
```

问题：

> 起算点、行为、报送对象均丢失。

Severity：

`ERROR`

---

# 58. 错误示例 04：AI解读进入事实层

原文：

> 金融企业应建立专项审计制度。

输出：

> 监管进一步强化了金融企业内部治理水平。

问题：

> S3越界解释。

Severity：

`ERROR`

---

# 59. 错误示例 05：擅自补对象

原文：

> 应及时报送有关情况。

上下文无法确认接收方。

错误：

> 应及时向财政部门报送有关情况。

如果原文没有“财政部门”：

> 不允许补充。

---

# 60. 错误示例 06：遗漏“原则上”

原文：

> 原则上不得……

输出：

> 不得……

虽然看似更简洁，但强度发生变化。

Severity：

`ERROR`

---

# 61. Error Handling

如果 JSON 生成失败：

```text
retry_count = 1
```

第一次重试：

> 原输入 + JSON错误提示。

第二次仍失败：

```text
status = failed
needs_human_review = true
```

不要无限循环。

---

# 62. 单条失败机制

Article 17失败：

```text
ART_001—ART_016 = completed
ART_017 = failed
ART_018以后 = pending
```

用户可以：

> Retry ART_017

不重跑前16条。

---

# 63. 人工修正

用户可以修改 Requirement。

例如：

```text
subject
condition
exception
```

修改后：

```text
review_status = HUMAN_LOCKED
```

S3重跑不得覆盖。

---

# 64. S3平台页面建议

S3不是后台黑盒。

前端建议：

## 左侧

法规条款列表：

```text
第1条 ✓
第2条 ✓
第3条 ⚠
第4条 ✓
...
```

---

## 中间

当前条款：

> 第十四条

### 原文

完整显示。

---

## 右侧

### 抽取结果

Requirement 01

```text
类型：义务
主体：金融企业
行为：……
条件：……
例外：……
```

Requirement 02

……

---

# 65. QC可视化

底部：

```text
Modal Check       ✓
Numeric Check     ✓
Exception Check   ✓
Evidence Binding  ✓
Confidence        98%
```

如果：

```text
Exception Check ⚠
```

用户点击查看具体问题。

---

# 66. 一键查看原文证据

点击 Requirement：

右侧或弹层高亮对应：

```text
source_text
```

未来 S4 也沿用同一 Evidence。

---

# 67. S3最终验收标准

## A. 完整性

所有 Article 处理率：

> 100%

不是说每条都有 Requirement。

定义条款等可能：

```text
has_requirement = false
```

但必须被处理。

---

## B. 数值

所有可识别监管数字：

> 100%进入数字校验流程。

---

## C. 条件

存在明确条件的 Requirement：

> 条件不得遗漏。

---

## D. 例外

存在明确但书/例外的：

> 必须结构化。

---

## E. Modal

法律义务强度：

> 不允许改变。

---

## F. Evidence

每个 Requirement：

> 必须绑定原文。

---

## G. AI越界

S3不得出现：

```text
监管趋严
进一步强化
体现监管意图
建议企业
应重点关注
```

等 S4 或机构内化层表达。

---

# 68. 建议测试样本

不能只测试一部《金融企业呆账核销管理办法》。

S3稳定性测试至少选择：

### 类型A：资产管理类

《金融企业呆账核销管理办法》

特点：

> 条件多、证据多、程序多。

### 类型B：行为监管类

选择支付、销售行为或消费者权益法规。

特点：

> 禁止事项多。

### 类型C：公司治理类

特点：

> 主体及职责多。

### 类型D：数据/科技类

特点：

> 原则性要求、开放概念较多。

### 类型E：资本/风险指标类

特点：

> 数字、比例、阈值多。

至少覆盖5类后再认为 S3 可以进入平台 MVP。

---

# 69. 当前S3设计中我认为需要特别注意的一个问题

虽然我们现在叫：

> “条款拆解与监管规则抽取”

但并不是所有法规都严格按照“第X条”组织。

未来可能出现：

- 通知；
- 指导意见；
- 答记者问；
- 监管问答；
- 公告；
- 附件；
- 表格；
- 技术标准；
- 业务规则。

因此底层不应该把所有处理对象永久写死为：

> Article。

更稳妥的是底层增加一个抽象对象：

```text
RegulatoryUnit
```

Article 是 RegulatoryUnit 的一种。

---

# 70. RegulatoryUnit建议

```json
{
  "unit_id": "",
  "unit_type": "ARTICLE",
  "label": "第十四条",
  "parent_unit_id": "",
  "order": 14,
  "original_text": ""
}
```

unit_type：

```text
ARTICLE
CHAPTER
PARAGRAPH
ITEM
SECTION
NOTICE_PARAGRAPH
ATTACHMENT
TABLE_ROW
OTHER
```

这样未来不需要重构数据库，就能支持更多形式的金融外规。

---

# 71. MVP怎么处理

MVP阶段前端仍然可以显示：

> “条款”。

但数据库底层我建议：

```text
RegulatoryUnit
```

而不是永远写死 Article。

这是一个现在多做一点、以后会省很多改造成本的设计。

---

# 72. S3 v1.0 结论

S3最终应该实现：

```text
原始监管文本
↓
最小监管单元
↓
监管动作
↓
主体
↓
条件
↓
例外
↓
时间/金额/比例
↓
审批/证据/报送
↓
Evidence
↓
QC
```

它的职责不是“聪明地解释法规”。

而是：

> **尽可能忠实、稳定、完整地把法规转化为机器可理解的监管事实。**

S3如果做稳，后面的S4才可以放心进行专业解读。

---

# 73. 下一步建议

下一步进入整个产品中最容易直接影响用户感受的一层：

# 《S4 外规解读 Skill Specification v1.0》

但 S4 我建议不要只做一个 Prompt，而拆成两个相互隔离的子模块：

### S4-A
**逐条外规解读**

负责：

> 第几条 + 外规原文 + 外规解读

### S4-B
**整体外规解读**

负责：

> 背景、目的、定位、适用范围、监管框架、核心要求、监管要点等。

两者均基于 S3 已经确认的 Requirement 和 Evidence 工作。

同时 S4 要重点建立你要求的语言质量控制：

> **实事求是、专业、逻辑清晰、客观、少形容词、少AI感、不夸大、不绝对化。**