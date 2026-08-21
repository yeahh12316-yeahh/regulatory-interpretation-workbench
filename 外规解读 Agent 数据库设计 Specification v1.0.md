# 外规解读 Agent 数据库设计 Specification v1.0

---

# 1. 文档定位

## 1.1 文档目的

本文档用于指导外规解读 Agent 平台数据库设计，为：

- 后端开发；
- 数据建模；
- API开发；
- 数据存储；
- 查询优化；

提供统一的数据结构规范。

---

# 1.2 设计目标

数据库设计需要支撑：

- 外规文件存储；
- AI处理流程；
- 条款结构化；
- 监管规则抽取；
- 外规解读；
- 新旧规比较；
- 证据追踪；
- QC审核；
- HTML展示；
- Word报告生成；
- 人工修改留痕。

---

# 1.3 设计原则

---

## 原则1：结构化优先

禁止：

将全部结果存储为单个JSON。

例如：

错误：

```text
regulation_result.json
```

正确：

拆分：

```text
regulations

articles

requirements

interpretations

evidence

```

---

## 原则2：对象独立

每个核心对象：

拥有独立生命周期。

包括：

- 法规；
- 条款；
- 监管要求；
- 解读；
- 证据。

---

## 原则3：全过程可追踪

所有核心表保存：

- 创建时间；
- 修改时间；
- 创建人；
- 版本；
- 状态。

---

## 原则4：支持AI重新运行

数据库设计需要支持：

- 单Skill重跑；
- 单条法规重跑；
- 单条款修复；
- 人工锁定。

---

# 2. 数据库总体架构

核心实体：

```text
tasks

        ↓

source_documents

        ↓

regulations

        ↓

articles

        ↓

requirements

        ↓

interpretations

        ↓

evidence


regulations

        ↓

version_relations

        ↓

changes


all objects

        ↓

qc_results

```

---

# 3. 数据库表设计总览

|表名|用途|
|-|-|
|tasks|任务管理|
|workflow_steps|流程状态|
|source_documents|输入文件|
|regulations|法规信息|
|articles|法规条款|
|requirements|监管规则|
|interpretations|法规解读|
|evidence|证据来源|
|version_relations|版本关系|
|article_mappings|条款映射|
|changes|新旧规变化|
|qc_results|质量检查|
|content_packages|输出内容包|
|audit_logs|审计日志|
|prompt_versions|Prompt版本|

---

# 4. tasks任务表

## 4.1 用途

管理一次完整外规解读任务。

---

## 4.2 表结构

|字段|类型|说明|
|-|-|-|
|task_id|UUID|任务ID|
|task_name|VARCHAR|任务名称|
|regulation_id|UUID|法规ID|
|status|ENUM|任务状态|
|current_step|VARCHAR|当前节点|
|created_by|VARCHAR|创建人|
|created_time|DATETIME|创建时间|
|updated_time|DATETIME|更新时间|
|priority|ENUM|优先级|

---

## 4.3 status

```text
CREATED

PROCESSING

WAITING_REVIEW

FAILED

COMPLETED

CANCELLED
```

---

# 5. workflow_steps流程表

## 5.1 用途

记录S1-S6及QC执行状态。

---

## 5.2 表结构

|字段|类型|说明|
|-|-|-|
|step_id|UUID|节点ID|
|task_id|UUID|任务ID|
|skill_name|VARCHAR|Skill名称|
|status|ENUM|状态|
|input_ids|JSON|输入对象|
|output_ids|JSON|输出对象|
|start_time|DATETIME|开始时间|
|end_time|DATETIME|结束时间|
|retry_count|INT|重试次数|
|error_message|TEXT|错误信息|

---

# 6. source_documents文件表

## 6.1 用途

保存：

- 法规原文；
- 官方解释；
- 历史版本；
- 参考材料。

---

## 6.2 表结构

|字段|类型|说明|
|-|-|-|
|document_id|UUID|文件ID|
|task_id|UUID|任务ID|
|file_name|VARCHAR|文件名|
|document_title|VARCHAR|文件标题|
|source_type|ENUM|来源类型|
|issuer|VARCHAR|发布机构|
|file_type|VARCHAR|文件类型|
|file_path|VARCHAR|存储地址|
|source_url|VARCHAR|来源地址|
|parse_status|ENUM|解析状态|
|ocr_confidence|DECIMAL|OCR置信度|
|created_time|DATETIME|创建时间|

---

# 7. regulations法规主表

## 7.1 用途

保存法规基础信息。

---

## 7.2 表结构

|字段|类型|说明|
|-|-|-|
|regulation_id|UUID|法规ID|
|title|VARCHAR|法规名称|
|short_title|VARCHAR|简称|
|document_no|VARCHAR|文号|
|issuer|VARCHAR|发文机构|
|publish_date|DATE|发布日期|
|effective_date|DATE|实施日期|
|status|ENUM|状态|
|document_type|VARCHAR|文件类型|
|industry_scope|JSON|行业范围|
|applicable_entities|JSON|适用机构|
|article_count|INT|条款数量|
|source_document_id|UUID|原文文件|

---

## 7.3 status

```text
DRAFT

FOR_COMMENT

EFFECTIVE

REVISED

REPEALED

EXPIRED

UNKNOWN
```

---

# 8. articles法规条款表

## 8.1 用途

保存法规原文最小单元。

---

## 8.2 表结构

|字段|类型|说明|
|-|-|-|
|article_id|UUID|条款ID|
|regulation_id|UUID|法规ID|
|article_no|VARCHAR|条款编号|
|chapter_name|VARCHAR|章节|
|article_order|INT|排序|
|original_text|TEXT|原文|
|page_start|INT|起始页|
|page_end|INT|结束页|
|has_requirement|BOOLEAN|是否包含要求|
|created_time|DATETIME|创建时间|

---

## 8.3 关键约束

original_text：

禁止修改。

---

# 9. requirements监管规则表

## 9.1 用途

保存S3输出的结构化监管规则。

---

## 9.2 表结构

|字段|类型|说明|
|-|-|-|
|requirement_id|UUID|规则ID|
|article_id|UUID|来源条款|
|rule_type|JSON|规则类型|
|subject|JSON|监管主体|
|action|TEXT|行为|
|object|TEXT|对象|
|condition|JSON|条件|
|exception|JSON|例外|
|deadline|JSON|期限|
|threshold|JSON|阈值|
|reporting|JSON|报送要求|
|approval|JSON|审批要求|
|source_text|TEXT|来源文本|
|confidence|DECIMAL|置信度|
|review_status|ENUM|审核状态|

---

# 10. interpretations法规解读表

## 10.1 用途

保存S4生成内容。

---

## 10.2 表结构

|字段|类型|说明|
|-|-|-|
|interpretation_id|UUID|解读ID|
|regulation_id|UUID|法规ID|
|article_id|UUID|条款ID|
|type|ENUM|解读类型|
|title|VARCHAR|标题|
|content|TEXT|解读内容|
|key_points|JSON|核心要点|
|fact_class|ENUM|事实类型|
|confidence|DECIMAL|置信度|
|version|INT|版本|
|human_lock|BOOLEAN|人工锁定|

---

## 10.3 fact_class

```text
FACT

OFFICIAL

INTERPRETATION

REFERENCE
```

---

# 11. evidence证据表

## 11.1 用途

保存：

结论来源。

---

## 11.2 表结构

|字段|类型|说明|
|-|-|-|
|evidence_id|UUID|证据ID|
|document_id|UUID|来源文件|
|article_id|UUID|条款|
|source_type|ENUM|来源类型|
|authority_level|INT|权威等级|
|source_text|TEXT|证据文本|
|page|INT|页码|
|location|JSON|位置|
|verified|BOOLEAN|是否验证|

---

# 12. version_relations版本关系表

## 12.1 用途

保存法规版本关系。

---

## 12.2 表结构

|字段|类型|说明|
|-|-|-|
|relation_id|UUID|关系ID|
|source_regulation_id|UUID|当前版本|
|target_regulation_id|UUID|历史版本|
|relation_type|ENUM|关系|
|evidence_ids|JSON|证据|
|confidence|DECIMAL|置信度|
|verified|BOOLEAN|确认|

---

# 13. article_mappings条款映射表

## 13.1 用途

支持新旧规条款对应。

---

## 13.2 表结构

|字段|类型|说明|
|-|-|-|
|mapping_id|UUID|映射ID|
|current_article_id|UUID|新规条款|
|previous_article_id|UUID|旧规条款|
|mapping_type|ENUM|映射类型|
|similarity_score|DECIMAL|相似度|
|confidence|DECIMAL|置信度|

---

# 14. changes变化表

## 14.1 用途

保存S5变化结果。

---

## 14.2 表结构

|字段|类型|说明|
|-|-|-|
|change_id|UUID|变化ID|
|current_article_id|UUID|新规条款|
|previous_article_id|UUID|旧规条款|
|change_type|ENUM|变化类型|
|current_text|TEXT|新文本|
|previous_text|TEXT|旧文本|
|summary|TEXT|变化说明|
|interpretation|TEXT|解释|
|confidence|DECIMAL|置信度|

---

# 15. qc_results质量检查表

## 15.1 用途

保存QC结果。

---

## 15.2 表结构

|字段|类型|说明|
|-|-|-|
|qc_id|UUID|检查ID|
|task_id|UUID|任务|
|target_type|VARCHAR|对象|
|target_id|UUID|对象ID|
|qc_type|VARCHAR|检查类型|
|severity|ENUM|严重程度|
|status|ENUM|结果|
|message|TEXT|问题|
|resolved|BOOLEAN|是否解决|

---

# 16. content_packages输出内容表

## 16.1 用途

支持HTML和Word统一输出。

---

## 16.2 表结构

|字段|类型|说明|
|-|-|-|
|package_id|UUID|内容包|
|regulation_id|UUID|法规|
|content_json|JSON|展示数据|
|version|INT|版本|
|hash|VARCHAR|内容Hash|
|created_time|DATETIME|时间|

---

# 17. audit_logs审计日志表

## 17.1 用途

满足金融机构审计要求。

---

## 17.2 表结构

|字段|类型|说明|
|-|-|-|
|log_id|UUID|日志ID|
|object_type|VARCHAR|对象|
|object_id|UUID|对象ID|
|action|VARCHAR|动作|
|operator|VARCHAR|操作人|
|before_data|JSON|修改前|
|after_data|JSON|修改后|
|time|DATETIME|时间|

---

# 18. prompt_versions Prompt版本表

## 18.1 用途

记录AI运行环境。

---

## 18.2 表结构

|字段|类型|说明|
|-|-|-|
|prompt_id|UUID|Prompt ID|
|skill_name|VARCHAR|Skill|
|version|VARCHAR|版本|
|prompt_text|TEXT|内容|
|model|VARCHAR|模型|
|created_time|DATETIME|时间|

---

# 19. 数据索引设计

重点索引：

---

## regulations

索引：

- title
- document_no
- issuer

---

## articles

索引：

- regulation_id
- article_no

---

## requirements

索引：

- rule_type
- subject
- action

---

## evidence

索引：

- article_id
- evidence_id

---

# 20. 数据库开发注意事项

---

## 20.1 不建议全部JSON存储

错误：

```text
all_result_json
```

原因：

无法：

- 查询；
- 修改；
- 建索引。

---

## 20.2 核心对象必须关系化

必须独立：

- Article；
- Requirement；
- Evidence。

---

## 20.3 AI结果需要版本化

禁止覆盖。

采用：

version机制。

---

## 20.4 人工修改必须留痕

所有修改进入：

audit_logs。

---

# 21. 数据库验收标准

完成后应支持：

## 查询

可以查询：

- 某法规；
- 某条款；
- 某监管要求；
- 某证据。

---

## 跳转

支持：

Article → Requirement → Evidence。

---

## 重跑

支持：

单Skill更新。

---

## 审计

支持：

查看：

谁修改、何时修改、修改什么。

---

# 22. 下一步

完成数据库设计后，建议进入：

# 《外规解读 Agent API Specification v1.0》

用于定义：

- 前后端接口；
- Workflow调用接口；
- 文件上传接口；
- AI任务接口；
- HTML读取接口；
- Word生成接口；
- 人工审核接口。

该文档完成后，后端和前端即可开始联调开发。