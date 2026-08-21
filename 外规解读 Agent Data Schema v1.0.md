# 外规解读 Agent Data Schema v1.0

## 1. 设计目标

本数据模型用于支撑金融行业外规解读 Agent 的完整处理链路，并作为以下模块的统一数据底座：

- 文件解析
- 法规识别
- 条款拆解
- 监管要求抽取
- 条款逐条解读
- 整体外规解读
- 新旧版本比较
- 证据绑定
- 质量校验
- HTML 交互页面
- Word 报告输出
- 人工复核
- 版本追踪

核心原则：

> **一次结构化，多处复用。**

HTML、Word、前端流程页及后续查询均不得重新生成一套独立内容。

---

# 2. 数据对象总览

建议第一阶段建立 9 类核心对象：

| 对象 | 作用 |
|---|---|
| `Task` | 管理一次完整解读任务 |
| `SourceDocument` | 管理用户上传或系统获取的文件 |
| `Regulation` | 管理一部法规的基本信息 |
| `Article` | 保存法规逐条原文 |
| `Requirement` | 保存从条款中拆出的监管规则 |
| `Interpretation` | 保存逐条及整体解读结果 |
| `Evidence` | 保存每项结论对应的证据 |
| `VersionRelation` | 管理法规版本及关联法规关系 |
| `QCResult` | 保存质量检查结果 |

建议关系：

```text
Task
│
├── SourceDocument
│
└── Regulation
      │
      ├── Article
      │     │
      │     ├── Requirement
      │     │
      │     ├── Interpretation
      │     │
      │     └── Evidence
      │
      ├── VersionRelation
      │
      ├── Interpretation
      │
      └── QCResult
```

---

# 3. Task Schema

## 3.1 对象用途

`Task` 是整个平台的流程主键。

用户从上传材料开始，到最终查看 HTML、下载 Word，始终应基于同一个 `task_id`。

不得在不同页面重新创建任务。

---

## 3.2 字段定义

| 字段 | 中文定义 | 类型 | 必填 | 来源/写入方 |
|---|---|---|---|---|
| `task_id` | 任务唯一编号 | string | 是 | 系统 |
| `task_name` | 任务名称 | string | 是 | 用户/系统 |
| `created_at` | 创建时间 | datetime | 是 | 系统 |
| `created_by` | 创建人 | string | 是 | 系统 |
| `updated_at` | 最近更新时间 | datetime | 是 | 系统 |
| `current_step` | 当前流程节点 | enum | 是 | Workflow |
| `task_status` | 总体任务状态 | enum | 是 | Workflow |
| `regulation_id` | 主法规ID | string | 否 | S1 |
| `source_document_ids` | 来源文件ID列表 | array | 是 | 输入层 |
| `processing_config` | 处理参数 | object | 是 | 用户 |
| `step_status` | 各节点运行状态 | object | 是 | Workflow |
| `error_state` | 当前错误 | object | 否 | 系统 |
| `last_checkpoint` | 最近断点 | object | 否 | Workflow |

---

## 3.3 状态枚举

### `task_status`

```text
created
processing
waiting_review
completed
failed
cancelled
```

### `current_step`

```text
INPUT
S1
S2
S3
S4
S5
S6
QC
OUTPUT
```

---

## 3.4 step_status 示例

```json
{
  "S1": {
    "status": "completed",
    "started_at": "2026-08-19T10:00:00",
    "completed_at": "2026-08-19T10:01:22",
    "version": 1
  },
  "S2": {
    "status": "completed",
    "version": 1
  },
  "S3": {
    "status": "running",
    "progress": 65
  },
  "S4": {
    "status": "pending"
  }
}
```

---

# 4. SourceDocument Schema

## 4.1 对象用途

管理所有输入资料。

不能只保存：

> “上传了一个 PDF”。

而要明确：

> 这个 PDF 是法规原文、答记者问、历史版本还是第三方材料。

---

## 4.2 字段

| 字段 | 中文定义 | 类型 | 必填 |
|---|---|---|---|
| `document_id` | 文件唯一编号 | string | 是 |
| `task_id` | 所属任务 | string | 是 |
| `file_name` | 原始文件名 | string | 是 |
| `document_title` | 文件实际标题 | string | 否 |
| `source_type` | 资料类型 | enum | 是 |
| `authority_level` | 来源权威等级 | integer | 是 |
| `issuer` | 发布机构 | array | 否 |
| `file_type` | PDF/Word/HTML等 | enum | 是 |
| `storage_uri` | 文件存储位置 | string | 是 |
| `source_url` | 官方来源地址 | string | 否 |
| `parsed_text` | 解析全文 | text | 否 |
| `ocr_required` | 是否OCR | boolean | 是 |
| `ocr_confidence` | OCR置信度 | number | 否 |
| `parse_status` | 解析状态 | enum | 是 |
| `is_primary_source` | 是否主文件 | boolean | 是 |
| `checksum` | 文件Hash | string | 是 |

---

## 4.3 source_type 枚举

```text
REGULATION_ORIGINAL
OFFICIAL_INTERPRETATION
OFFICIAL_QA
ISSUANCE_NOTICE

PREVIOUS_VERSION
RELATED_REGULATION
SUPERIOR_REGULATION
SUPPORTING_RULE

CONSULTING_REPORT
LAW_FIRM_REPORT
INDUSTRY_REPORT
OTHER_REFERENCE
```

---

# 5. Regulation Schema

## 5.1 对象用途

保存一部法规的身份信息。

它相当于法规知识库的“主表”。

---

## 5.2 字段

| 字段 | 中文定义 | 类型 | 必填 | 写入节点 |
|---|---|---|---|---|
| `regulation_id` | 法规唯一ID | string | 是 | S1 |
| `title` | 法规名称 | string | 是 | S1 |
| `short_title` | 简称 | string | 否 | S1/S4 |
| `document_no` | 文号 | string | 否 | S1 |
| `issuer` | 发文机构 | array | 是 | S1 |
| `publish_date` | 发布日期 | date | 否 | S1 |
| `effective_date` | 实施日期 | date | 否 | S1 |
| `expiry_date` | 失效日期 | date | 否 | S2 |
| `status` | 效力状态 | enum | 是 | S2 |
| `document_type` | 文件类型 | string | 否 | S2 |
| `regulation_level` | 法规层级 | string | 否 | S2 |
| `industry_scope` | 涉及金融行业领域 | array | 否 | S2 |
| `applicable_entities` | 明确适用机构 | array | 否 | S2 |
| `applicable_businesses` | 适用业务范围 | array | 否 | S2 |
| `chapter_count` | 章节数量 | integer | 否 | S1 |
| `article_count` | 条款数量 | integer | 是 | S1 |
| `attachment_count` | 附件数量 | integer | 否 | S1 |
| `primary_document_id` | 对应法规原文文件ID | string | 是 | S1 |
| `official_supporting_documents` | 官方辅助材料 | array | 否 | S2 |
| `summary_status` | 整体解读状态 | enum | 是 | S4 |

---

## 5.3 status 枚举

```text
DRAFT
FOR_COMMENT
NOT_EFFECTIVE
EFFECTIVE
REVISED
REPEALED
EXPIRED
UNKNOWN
```

如无法确认：

> 必须使用 `UNKNOWN`

不得由模型自行推断。

---

# 6. Article Schema

## 6.1 对象用途

保存逐条法规原文。

这是实现：

> 第几条 + 外规原文 + 外规解读

的基础。

---

## 6.2 字段

| 字段 | 中文定义 | 类型 | 必填 |
|---|---|---|---|
| `article_id` | 条款唯一ID | string | 是 |
| `regulation_id` | 所属法规 | string | 是 |
| `chapter_id` | 所属章节 | string | 否 |
| `chapter_title` | 章节名称 | string | 否 |
| `article_no` | 条款编号 | string | 是 |
| `article_order` | 排序编号 | integer | 是 |
| `original_text` | 条款完整原文 | text | 是 |
| `normalized_text` | 清洗后的文本 | text | 是 |
| `page_start` | 起始页 | integer | 否 |
| `page_end` | 结束页 | integer | 否 |
| `source_document_id` | 原文文件ID | string | 是 |
| `source_location` | 精确位置 | object | 否 |
| `article_type` | 条款类型 | array | 否 |
| `has_numeric_rule` | 是否含数值要求 | boolean | 是 |
| `has_exception` | 是否含例外 | boolean | 是 |
| `requirement_count` | 提取要求数量 | integer | 是 |
| `interpretation_status` | 解读状态 | enum | 是 |
| `human_lock` | 是否人工锁定 | boolean | 是 |

---

## 6.3 原文完整性要求

`original_text`：

- 不得摘要；
- 不得改写；
- 不得修正语病；
- 不得补充标点；
- OCR疑似错误必须单独记录。

---

# 7. Requirement Schema

这是整套系统最重要的数据模型。

---

## 7.1 对象用途

将法律条文转换为机器可理解的监管规则。

一条 Article 可以对应多个 Requirement。

---

## 7.2 字段

| 字段 | 中文定义 | 类型 | 必填 |
|---|---|---|---|
| `requirement_id` | 监管规则唯一ID | string | 是 |
| `article_id` | 来源条款 | string | 是 |
| `regulation_id` | 来源法规 | string | 是 |
| `rule_type` | 规则类型 | array | 是 |
| `subject` | 监管对象/责任主体 | array | 否 |
| `action` | 要求行为 | string | 否 |
| `object` | 行为对象 | string | 否 |
| `condition` | 适用条件 | array | 否 |
| `exception` | 例外/除外情形 | array | 否 |
| `deadline` | 时限 | object | 否 |
| `frequency` | 频率 | object | 否 |
| `threshold` | 阈值 | array | 否 |
| `amount` | 金额要求 | array | 否 |
| `ratio` | 比例要求 | array | 否 |
| `evidence_requirement` | 证据要求 | array | 否 |
| `approval_requirement` | 审批要求 | object | 否 |
| `reporting_requirement` | 报送要求 | object | 否 |
| `penalty` | 法律后果/处罚 | object | 否 |
| `related_requirement_ids` | 关联规则 | array | 否 |
| `source_text` | 对应原文片段 | text | 是 |
| `fact_class` | 内容性质 | enum | 是 |
| `confidence` | 提取置信度 | number | 是 |
| `review_status` | 复核状态 | enum | 是 |

---

# 8. rule_type 标准枚举

建议第一阶段固定：

```text
DEFINITION
SCOPE
PRINCIPLE

OBLIGATION
PROHIBITION
PERMISSION
CONDITION
EXCEPTION

PROCEDURE
APPROVAL
EVIDENCE

TIME_LIMIT
FREQUENCY
THRESHOLD
AMOUNT
RATIO

REPORTING
DISCLOSURE

GOVERNANCE
AUDIT
RESPONSIBILITY
PENALTY

TRANSITION

RIGHT
TERMINATION
OTHER
```

不允许 LLM 自己新增分类。

如无法分类：

> `OTHER`

并进入人工复核。

---

# 9. 数字字段必须结构化

禁止只保存：

> “2年内完成”。

应该保存：

```json
{
  "value": 2,
  "unit": "year",
  "operator": "<=",
  "reference_point": "核销完成日",
  "original_expression": "呆账核销后2年内"
}
```

---

## 9.1 时间结构

```json
{
  "value": 6,
  "unit": "month",
  "operator": "<=",
  "reference_point": "会计年度终了",
  "original_expression": "每个会计年度终了后6个月内"
}
```

---

# 10. Interpretation Schema

## 10.1 对象用途

同时管理：

- 条款逐条解读；
- 整体法规解读。

---

## 10.2 字段

| 字段 | 中文定义 | 类型 | 必填 |
|---|---|---|---|
| `interpretation_id` | 解读唯一ID | string | 是 |
| `regulation_id` | 法规ID | string | 是 |
| `article_id` | 条款ID | string | 条款解读时必填 |
| `interpretation_type` | 解读类型 | enum | 是 |
| `title` | 解读标题 | string | 是 |
| `summary` | 简要概括 | text | 否 |
| `interpretation_text` | 正式解读 | text | 是 |
| `key_points` | 监管要点 | array | 否 |
| `linked_requirement_ids` | 关联监管规则 | array | 是 |
| `related_article_ids` | 关联条款 | array | 否 |
| `evidence_ids` | 证据 | array | 是 |
| `fact_class` | 内容性质 | enum | 是 |
| `confidence` | 置信度 | number | 是 |
| `review_status` | 审核状态 | enum | 是 |
| `content_version` | 内容版本 | integer | 是 |
| `human_lock` | 人工锁定 | boolean | 是 |
| `generated_by` | AI/人工 | enum | 是 |
| `created_at` | 创建时间 | datetime | 是 |
| `updated_at` | 修改时间 | datetime | 是 |

---

# 11. interpretation_type

建议固定：

```text
ARTICLE
BACKGROUND
PURPOSE
POSITIONING
SCOPE
FRAMEWORK
CORE_REQUIREMENT
DUTY
PROHIBITION
EVIDENCE
PROCEDURE
REPORTING
NUMERIC
TRANSITION
VERSION_CHANGE
EXECUTIVE_SUMMARY
OTHER
```

---

# 12. 逐条解读的必填输出

当：

```text
interpretation_type = ARTICLE
```

必须保证：

```text
article_id
interpretation_text
linked_requirement_ids
evidence_ids
fact_class
confidence
```

全部存在。

---

# 13. 逐条解读建议额外结构

建议增加：

```json
{
  "article_summary": "",
  "regulatory_subject": [],
  "key_requirements": [],
  "conditions": [],
  "exceptions": [],
  "important_numbers": [],
  "related_articles": [],
  "interpretation_note": ""
}
```

这样 HTML 不必再次从正文里做文本抽取。

---

# 14. Fact Class

所有生成内容必须标记：

```text
FACT
OFFICIAL
INTERPRETATION
REFERENCE
```

规则：

### FACT
外规原文明示。

### OFFICIAL
监管官方说明。

### INTERPRETATION
Agent形成的分析。

### REFERENCE
外部研究材料观点。

---

# 15. Evidence Schema

## 15.1 目标

所有重要结论必须能够完成：

> 结论 → Evidence → 原始文件 → 条款/位置

---

## 15.2 字段

| 字段 | 中文定义 | 类型 | 必填 |
|---|---|---|---|
| `evidence_id` | 证据ID | string | 是 |
| `document_id` | 来源文件 | string | 是 |
| `regulation_id` | 法规ID | string | 否 |
| `article_id` | 条款ID | string | 否 |
| `source_type` | 来源类型 | enum | 是 |
| `authority_level` | 权威等级 | integer | 是 |
| `source_text` | 原始证据文本 | text | 是 |
| `source_location` | 原文位置 | object | 是 |
| `source_url` | 官方来源 | string | 否 |
| `evidence_purpose` | 支持什么结论 | string | 是 |
| `verified` | 是否完成验证 | boolean | 是 |

---

# 16. source_location

建议支持：

```json
{
  "page": 12,
  "article_id": "ART_014",
  "paragraph": 2,
  "text_start_offset": 1056,
  "text_end_offset": 1289
}
```

HTML 跳转以后才能做到：

> 不是仅跳到页面，而是尽量定位到相关原文。

---

# 17. Evidence 权威等级

```text
1 = 外规正式原文
2 = 监管机构官方解读/答记者问
3 = 直接关联的正式法规
4 = 行业协会/专业机构
5 = 咨询机构/律师事务所
6 = 其他研究材料
```

---

# 18. Evidence 约束

以下内容：

- 监管义务
- 禁止要求
- 报送要求
- 时限
- 金额
- 比例
- 处罚
- 适用范围

原则上必须至少存在：

> Level 1 或 Level 2 Evidence。

不得仅使用 Level 4—6。

---

# 19. VersionRelation Schema

## 19.1 用途

解决最容易发生错误的：

> “历史版本”和“直接前序版本”混淆问题。

---

## 19.2 字段

| 字段 | 含义 | 类型 |
|---|---|---|
| `relation_id` | 关系ID | string |
| `source_regulation_id` | 当前法规 | string |
| `target_regulation_id` | 关联法规 | string |
| `relation_type` | 关系类型 | enum |
| `evidence_id` | 关系证明 | string |
| `confidence` | 置信度 | number |
| `verified` | 是否确认 | boolean |

---

# 20. relation_type

```text
DIRECT_PREVIOUS_VERSION
HISTORICAL_VERSION
REPEALS
REVISES
REPLACES

SUPERIOR_RULE
SUBORDINATE_RULE

SUPPORTING_RULE
RELATED_RULE
CITES
UNKNOWN
```

---

# 21. 新旧规差异对象

建议单独建立：

```json
{
  "change_id": "",
  "current_article_id": "",
  "previous_article_id": "",
  "change_type": "",
  "current_text": "",
  "previous_text": "",
  "change_summary": "",
  "interpretation": "",
  "evidence_ids": [],
  "confidence": 0.95
}
```

---

# 22. Change Type

固定：

```text
ADDED
DELETED
REVISED
CLARIFIED
DETAILED

EXPANDED_SCOPE
NARROWED_SCOPE

TIGHTENED
RELAXED

PROCESS_CHANGED
TIME_CHANGED
THRESHOLD_CHANGED

WORDING_CHANGED
NO_SUBSTANTIVE_CHANGE
UNCERTAIN
```

如果不确定：

> `UNCERTAIN`

不允许为了填满表格而强行判断。

---

# 23. QCResult Schema

## 23.1 用途

每个 Skill 和最终内容都必须产生 QC 记录。

---

## 23.2 字段

| 字段 | 中文定义 | 类型 |
|---|---|---|
| `qc_id` | QC编号 | string |
| `task_id` | 任务ID | string |
| `target_type` | 被检查对象类型 | enum |
| `target_id` | 被检查对象ID | string |
| `qc_type` | 检查类型 | enum |
| `severity` | 严重程度 | enum |
| `status` | 检查结果 | enum |
| `message` | 问题描述 | text |
| `evidence` | 支持信息 | object |
| `auto_fixable` | 是否可自动修正 | boolean |
| `resolved` | 是否已解决 | boolean |
| `resolved_by` | 解决人 | string |
| `resolved_at` | 解决时间 | datetime |

---

# 24. qc_type

建议至少包括：

```text
SOURCE_CHECK
ARTICLE_COMPLETENESS
ARTICLE_SEQUENCE

NUMERIC_CHECK
DATE_CHECK
RATIO_CHECK

EVIDENCE_BINDING
VERSION_CHECK

FACT_INTERPRETATION_CHECK
EXCEPTION_CHECK
NEGATION_CHECK

LANGUAGE_STYLE_CHECK
ABSOLUTE_STATEMENT_CHECK
OVER_INTERPRETATION_CHECK

NAVIGATION_CHECK
LINK_CHECK
OUTPUT_CONSISTENCY
```

注意最后三个非常重要。

QC不只检查内容，还要检查：

> 网页跳转是否正常。

---

# 25. Severity

```text
INFO
WARNING
ERROR
BLOCKER
```

---

# 26. BLOCKER 一票否决项

以下错误不得自动发布最终报告：

### 法规事实错误

如：

- 日期错误
- 金额错误
- 比例错误
- 条款引用错误

### 原意错误

如：

- “可以”变成“应当”
- “原则上”变成“必须”
- “不得”被遗漏

### 关键限定条件遗漏

如：

> 条款原文存在“除……外”，解读遗漏例外。

### 错误版本比较

将非直接前序版本作为直接前序版比较。

### Evidence 缺失

核心监管结论无原文依据。

### 导航错误

HTML 页面：

> 用户点击“查看第14条”，实际进入第15条。

这同样应视为发布阻断问题。

---

# 27. Review Status

所有 AI 内容统一：

```text
AI_DRAFT
AUTO_CHECKED
HUMAN_REVIEW_REQUIRED
HUMAN_REVIEWED
HUMAN_LOCKED
REJECTED
```

---

# 28. 人工编辑版本模型

任何人工修改均生成新版本。

例如：

```json
{
  "content_version": 3,
  "previous_version": 2,
  "change_type": "human_edit",
  "changed_by": "user_001",
  "changed_at": "2026-08-19T15:20:00",
  "change_reason": "调整解读表述"
}
```

不能直接覆盖旧版本。

---

# 29. HTML 页面路由数据模型

这是平台开发需要提前锁死的部分。

建议核心 URL：

```text
/tasks/{task_id}
```

任务流程：

```text
/tasks/{task_id}/input
/tasks/{task_id}/parse
/tasks/{task_id}/scope
/tasks/{task_id}/requirements
/tasks/{task_id}/interpretation
/tasks/{task_id}/comparison
/tasks/{task_id}/qc
/tasks/{task_id}/result
```

最终法规：

```text
/tasks/{task_id}/result/overview
```

逐条解读：

```text
/tasks/{task_id}/result/articles/{article_id}
```

监管要求：

```text
/tasks/{task_id}/result/requirements/{requirement_id}
```

证据：

```text
/tasks/{task_id}/result/evidence/{evidence_id}
```

---

# 30. 禁止用展示文本作为 URL 主键

错误：

```text
/article/第十四条
```

正确：

```text
/article/FIN_MOF_2017_90_ART_014
```

显示名称可以叫：

> 第十四条

但程序必须依赖：

> `article_id`

---

# 31. 页面统一 Navigation Object

建议前端读取：

```json
{
  "current_article_id": "ART_014",
  "previous_article_id": "ART_013",
  "next_article_id": "ART_015",
  "related_article_ids": ["ART_016"],
  "parent_regulation_id": "FIN_MOF_2017_90"
}
```

这样：

- 上一条
- 下一条
- 关联条款
- 返回法规

全部通过 ID 跳转。

---

# 32. 页面历史位置

为解决用户从：

> 第14条 → 第16条 → 返回

建议维护：

```json
{
  "from_route": "",
  "from_article_id": "",
  "from_requirement_id": "",
  "scroll_position": 1265
}
```

返回时恢复原位置。

---

# 33. Word Report Schema

Word 不建议直接接受自然语言 Prompt。

应接收：

```text
ReportData
```

---

## 33.1 ReportData

```json
{
  "cover": {},
  "basic_info": {},
  "executive_summary": [],
  "background": [],
  "purpose": [],
  "positioning": [],
  "scope": [],
  "framework": [],
  "core_requirements": [],
  "duties": [],
  "prohibitions": [],
  "evidence_requirements": [],
  "procedures": [],
  "reporting": [],
  "numeric_requirements": [],
  "version_changes": [],
  "article_interpretations": [],
  "references": []
}
```

所有字段均从：

> Regulation Data Model

读取。

---

# 34. HTML 与 Word 内容一致性

建议增加：

```text
content_hash
```

例如 Interpretation：

```json
{
  "interpretation_id": "INT_014",
  "content_version": 4,
  "content_hash": "abc123..."
}
```

Word 和 HTML 均记录：

> `content_hash`

如果两个 Renderer 使用内容不同：

QC：

```text
OUTPUT_CONSISTENCY = ERROR
```

---

# 35. S1-S6 写权限

这是防止 Skill 相互覆盖的重要规则。

| 对象 | S1 | S2 | S3 | S4 | S5 | S6 |
|---|---:|---:|---:|---:|---:|---:|
| Regulation基础信息 | 写 | 补充 | 读 | 读 | 读 | 读 |
| Article原文 | 写 | 读 | 读 | 读 | 读 | 读 |
| Requirement | - | - | 写 | 读 | 读 | 读 |
| Interpretation | - | - | - | 写 | 写部分 | 读/组织 |
| Evidence | 写部分 | 写 | 写 | 写 | 写 | 绑定 |
| VersionRelation | - | 写 | 读 | 读 | 写/校验 | 读 |
| ReportData | - | - | - | - | - | 写 |

特别规定：

> **S4不得修改 Article.original_text。**

> **S6不得修改 Requirement 监管事实。**

---

# 36. 前端页面与数据对象映射

## 文件解析页

读取：

```text
Task
SourceDocument
Regulation
Article
```

---

## 法规识别页

读取：

```text
Regulation
VersionRelation
```

---

## 条款拆解页

读取：

```text
Article
Requirement
```

---

## 解读页

读取：

```text
Article
Requirement
Interpretation
Evidence
```

---

## 新旧规比较页

读取：

```text
VersionRelation
Change Object
```

---

## QC页

读取：

```text
QCResult
```

---

## 最终结果页

读取：

```text
ReportData
+
Regulation Data Model
```

---

# 37. 数据完整性校验

每次进入 S4 前必须检查：

```text
Regulation 存在
Article 数量 > 0
所有 Article 均有 original_text
S3处理完成率 = 100%
BLOCKER QC = 0
```

否则：

> S4不得启动。

---

# 38. 最终报告发布前校验

至少检查：

```text
法规基本信息完整
条款数量一致
逐条解读覆盖率
Evidence绑定率
数字校验结果
版本关系校验
Fact/Interpretation标签
BLOCKER问题数量
HTML链接测试
Word/HTML一致性
```

---

# 39. 建议的发布阈值

第一阶段可以设置：

| 指标 | 建议要求 |
|---|---:|
| 条款原文解析覆盖率 | 100% |
| 逐条处理覆盖率 | 100% |
| 数值核验覆盖率 | 100% |
| 核心结论证据绑定率 | 100% |
| BLOCKER | 0 |
| ERROR | 0 |
| HTML内部链接有效率 | 100% |
| Word/HTML内容一致性 | 100% |

这里的“100%”主要指：

> 系统是否完成了检查和绑定，

而不是声称：

> AI内容准确率100%。

两者必须区分。

---

# 40. Prompt 层需要读取什么

后面每个 Prompt 不允许直接读取整个数据库。

只向对应 Skill 提供它需要的数据。

例如 S4 单条解读输入：

```json
{
  "regulation": {
    "title": "",
    "document_no": "",
    "issuer": []
  },

  "article": {
    "article_id": "",
    "article_no": "",
    "original_text": ""
  },

  "requirements": [],

  "official_evidence": [],

  "related_articles": []
}
```

这样减少模型自行跨条款发挥。

---

# 41. 建议第一阶段数据库实体

开发 MVP 时至少建立：

```text
tasks

source_documents

regulations

articles

requirements

interpretations

evidence

version_relations

regulation_changes

qc_results

content_versions
```

不要把所有内容塞进一个：

```text
result_json
```

短期虽然开发快，但后续：

- 跳转
- 修改
- 复核
- 版本追踪
- 单条重跑
- 搜索

都会变得困难。

---

# 42. 允许使用 JSONB 的位置

部分复杂字段可以存 JSONB：

```text
processing_config
step_status
source_location

condition
exception
threshold

deadline
frequency

approval_requirement
reporting_requirement
```

但核心对象：

```text
Article
Requirement
Interpretation
Evidence
```

应独立成表。

---

# 43. ID设计建议

ID 必须：

- 稳定
- 唯一
- 不依赖显示文字
- 不因用户修改标题而变化

建议：

```text
task_id
TASK_20260819_000001

regulation_id
REG_01J9...

article_id
ART_01J9...

requirement_id
REQ_01J9...

interpretation_id
INT_01J9...

evidence_id
EVI_01J9...
```

实际开发更建议采用：

> UUID / ULID

而不是靠人工拼文号作为真正数据库主键。

文号可以作为：

> `business_key`

---

# 44. 为什么不建议文号直接作为主键

现实中可能出现：

- 无文号法规；
- 征求意见稿；
- 同一文件多个版本；
- 文号录入差异；
- 中文全角半角问题。

因此建议：

```text
id = ULID
business_key = 财金〔2017〕90号
```

---

# 45. 搜索索引建议

平台未来至少需要支持：

### 法规搜索

```text
法规名称
文号
发文机构
```

### 条款搜索

```text
original_text
article_no
```

### 解读搜索

```text
interpretation_text
key_points
```

### 监管规则搜索

```text
subject
action
rule_type
threshold
```

---

# 46. 第一阶段不要过度设计的内容

Data Schema v1.0 暂时不需要：

- 企业内部制度
- 企业业务流程
- 部门职责
- 控制措施
- 整改建议
- 内控缺陷
- 合规差距

因为这些已经进入：

> 外规内化。

当前 Agent 不做。

---

# 47. Data Schema v1.0 最关键的五张表

如果开发团队希望先做极简版，我建议优先保证：

```text
Regulation
Article
Requirement
Interpretation
Evidence
```

关系：

```text
Regulation
   ↓
Article
   ↓
Requirement
   ↓
Interpretation
   ↓
Evidence
```

不过正式平台仍建议保留 Task 和 QC。

---

# 48. Benchmark 验证方式

继续使用：

> 《金融企业呆账核销管理办法（2017年版）》

作为 Benchmark 01。

第一轮不要求生成完整 Word。

先验证数据是否能够稳定形成：

```text
1个 Regulation

N个 Article

每条 Article
    ↓
0-N个 Requirement
    ↓
1个逐条 Interpretation
    ↓
若干 Evidence
```

重点测试：

- 条款是否遗漏
- 条件是否丢失
- 例外是否丢失
- 数字是否准确
- 证据是否正确
- Article跳转是否稳定

---

# 49. 下一步正式进入 Prompt 设计

完成 Data Schema 后，就可以开始写 Prompt。

但仍不建议一次性写6个。

建议先做：

# S3 条款拆解与监管规则抽取 Skill

原因是：

> S3 是后续外规解读准确性的事实底座。

下一份建议直接形成：

# 《S3 条款拆解与监管规则抽取 Skill Specification v1.0》

其中包含：

1. Skill定位  
2. System Prompt  
3. Input JSON Schema  
4. Output JSON Schema  
5. 监管规则识别方法  
6. 条件识别规则  
7. 例外识别规则  
8. 数字提取规则  
9. 否定词处理规则  
10. “应当 / 可以 / 不得 / 原则上”等法律措辞处理规则  
11. 多重义务拆解规则  
12. 跨条款关联规则  
13. 证据绑定规则  
14. Confidence规则  
15. Error Handling  
16. QC规则  
17. Benchmark测试案例  
18. 正确输出示例  
19. 错误输出示例  
20. 验收标准

**先把 S3 做到足够稳定，再进入 S4 逐条解读。**