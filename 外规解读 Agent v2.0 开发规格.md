# 外规解读 Agent v2.0 开发规格

## 一、总体定位

### 1. 产品定位

本 Agent 面向金融行业相关机构，适用于银行、保险、证券、基金、期货、信托、金融租赁、消费金融、支付机构、财务公司、小额贷款、融资担保等金融或类金融机构。

本 Agent **仅承担“外规解读”职责**，不承担：

- 外规内化
- 制度差距分析
- 整改建议生成
- 控制设计
- 内控评价
- 审计测试

Agent 的目标是：

> 将监管外规转化为准确、完整、结构化、可追溯、可阅读的法规解读结果，并通过 Word 报告和 HTML 交互页面进行统一呈现。

---

# 二、核心设计原则

## 2.1 实事求是

所有监管事实优先来源于：

1. 外规原文
2. 监管机构正式发布材料
3. 监管机构答记者问、官方解读
4. 直接前序版本及关联法规
5. 其他研究材料

不得依据第三方观点修改监管原意。

---

## 2.2 专业、客观、克制

输出应：

- 减少形容词
- 减少宣传式表达
- 减少口号化总结
- 避免夸张
- 避免绝对化
- 避免未经证明的趋势判断
- 避免“AI腔”

例如：

不建议：

> 本次监管规则实现了金融资产管理体系的全面重塑。

建议：

> 本次规则对金融资产管理范围、执行标准及管理要求进行了调整和细化。

---

## 2.3 事实与解读分离

所有内容至少分为三类：

### F｜Fact
监管原文明确规定。

### O｜Official
监管机构官方解读或答记者问明确说明。

### I｜Interpretation
Agent 基于原文和官方材料形成的解释。

Agent 不得将 I 类内容包装成 F 类事实。

---

## 2.4 先结构化，再生成内容

禁止采用：

> “上传 PDF → 大模型直接输出报告”

的模式。

统一流程必须为：

```text
文件
↓
结构化法规对象
↓
条款对象
↓
监管要求对象
↓
解读对象
↓
证据对象
↓
页面 / Word / JSON
```

Word 和 HTML 必须来源于**同一套结构化数据**。

---

# 三、平台整体技术架构

```text
【输入层】

监管外规
官方辅助材料
历史版本
关联法规
任务参数

        ↓

【S1 文件解析与元数据识别】

        ↓

【S2 法规关系与适用范围识别】

        ↓

【S3 条款拆解与监管规则抽取】

        ↓

【S4 条款解读与整体法规解读】

        ↓

【S5 新旧版本比较与变化识别】

        ↓

【S6 内容编排与证据绑定】

        ↓

【质量控制 QC Engine】

        ↓

【统一 Regulation Data Model】

       ↙                ↘

【HTML Renderer】    【Word Renderer】

       ↓                  ↓

交互式外规解读       正式外规解读报告
```

注意：

**HTML Renderer 和 Word Renderer 不属于 LLM Skill。**

其职责是：

> 将已经确认的数据渲染出来。

不得让 Word 生成器再次调用模型重新总结一遍，也不得让 HTML 页面重新调用模型改写内容。

---

# 四、核心数据模型

这是整个系统是否能够真正“跳转、联动、持续运行”的关键。

---

## 4.1 Regulation Object

每部法规只有一个主对象。

```json
{
  "regulation_id": "FIN_MOF_2017_90",
  "title": "金融企业呆账核销管理办法（2017年版）",
  "document_no": "财金〔2017〕90号",
  "issuer": ["财政部"],
  "publish_date": "",
  "effective_date": "2017-10-01",
  "status": "effective",
  "document_type": "规范性文件",
  "industry_scope": [],
  "applicable_entities": [],
  "source_file_id": "",
  "version_id": "",
  "previous_version_id": "",
  "processing_status": {}
}
```

`regulation_id` 一经生成原则上不得修改。

---

# 五、Article Object——条款对象

法规每一条形成独立对象。

例如：

```json
{
  "article_id": "FIN_MOF_2017_90_ART_014",
  "regulation_id": "FIN_MOF_2017_90",
  "article_no": "第十四条",
  "chapter_no": "第四章",
  "article_order": 14,
  "original_text": "……",
  "source_page": 6,
  "source_offset": {},
  "article_type": [],
  "interpretation_status": "completed"
}
```

这里必须保留：

> **完整外规原文。**

不得只存摘要。

否则未来无法实现：

> 解读 → 原文

的精确跳转。

---

# 六、Requirement Object——监管规则对象

这是 S3 最重要的输出。

一条法规可以拆出多个 Requirement。

例如：

```json
{
  "requirement_id": "FIN_MOF_2017_90_ART_014_REQ_001",

  "article_id": "FIN_MOF_2017_90_ART_014",

  "subject": "金融企业",

  "rule_type": "obligation",

  "action": "加强已核销资产管理",

  "object": "已核销债权或股权",

  "condition": "除权利义务已经终结外",

  "deadline": null,

  "frequency": null,

  "threshold": null,

  "exception": "权利义务已经终结",

  "evidence_required": null,

  "related_articles": [],

  "source_text": "……",

  "confidence": 0.99
}
```

---

# 七、监管规则类型 Taxonomy

S3 不得只有“义务/禁止”。

建议统一采用：

```text
DEF     定义
SCOPE   适用范围

PRIN    原则

OBL     义务
PROH    禁止
PERM    授权 / 可以
COND    条件
EXCP    例外

PROC    程序
APPR    审批
EVID    证据

TIME    时限
FREQ    频率
THRE    阈值

RPT     报告 / 报送
DISC    披露

GOV     治理职责
AUD     审计监督
RESP    责任追究

PEN     处罚

TRANS   过渡期

RIGHT   权利
END     权利义务终止
```

一个监管要求可以包含多个标签。

---

# 八、Interpretation Object——解读对象

每一条法规至少产生一个条款解读对象。

```json
{
  "interpretation_id": "FIN_MOF_2017_90_ART_014_INT_001",

  "article_id": "FIN_MOF_2017_90_ART_014",

  "summary": "",

  "interpretation": "",

  "regulatory_meaning": "",

  "key_points": [],

  "conditions": [],

  "exceptions": [],

  "linked_requirements": [],

  "evidence_ids": [],

  "content_type": "Interpretation",

  "confidence": 0.94,

  "review_status": "pending"
}
```

---

# 九、逐条解读的标准结构

未来 HTML 和 Word 均采用统一结构：

## 第十四条

### 外规原文

> 原文完整展示……

### 外规解读

说明：

- 本条监管对象是什么；
- 本条规定什么事项；
- 什么情况下适用；
- 是否存在例外；
- 是否涉及时间、金额、比例、频率；
- 与其他条款是什么关系；
- 本条的监管含义是什么。

### 监管要点

`账销案存`

`持续追偿`

`资产保全`

### 规则属性

义务性要求

### 关联条款

第十五条  
第十六条

### 内容性质

`原文事实 + Agent解读`

### 查看证据

点击后定位至对应原文。

---

# 十、S1——文件解析与元数据识别

## Input

```text
原始法规文件
辅助附件
用户任务参数
```

## Output

```text
Regulation Object
Chapter List
Article List
Document Metadata
```

## S1 主要工作

识别：

- 法规名称
- 文号
- 发文机构
- 发布日期
- 实施日期
- 章节
- 条款
- 附件
- 附则
- 修订标识
- 废止标识

## 强制校验

### QC-S1-01

法规名称不得仅根据文件名判断。

必须以正文标题为主要依据。

### QC-S1-02

条款顺序必须连续性检查。

例如：

```text
第1条
第2条
第4条
```

则必须提示：

> 疑似遗漏第3条，请检查文件解析结果。

### QC-S1-03

OCR低置信区域不得直接进入后续流程。

---

# 十一、S2——法规关系与适用范围识别

## Input

Regulation Object  
Article Objects  
历史法规材料  
官方辅助材料

## Output

```text
法规定位
适用主体
适用业务
法规关系
版本关系
```

## 必须区分

### 原文明确适用

例如：

> 本办法适用于……

标记：

`FACT`

### Agent判断适用

例如根据机构性质分析可能适用。

如果未来外规解读范围内确实需要输出，应标记：

`INTERPRETATION`

不得混淆。

---

# 十二、S3——条款拆解与监管规则抽取

这是整个 Agent 的核心事实层。

原则：

> S3只负责“法规写了什么”。

暂不负责：

> “这意味着什么”。

---

## 输入

Article Object

## 输出

Requirement Objects

---

## 每条必须识别

```text
监管主体
监管对象

行为
条件
例外

时间
频率
金额
比例
数量

审批
报送
披露
审计

授权
禁止
责任

法律后果
```

---

## 关键规则

例如：

原文：

> 金融企业应在每个会计年度终了后6个月内……

必须拆成：

```text
主体：
金融企业

行为：
报送

事项：
上年度呆账核销情况及专项审计报告

期限：
每个会计年度终了后6个月内

对象：
同级财政部门
```

不得只输出：

> 金融企业应及时向财政部门报送有关情况。

因为这已经丢失了关键事实。

---

# 十三、S4——法规解读

S4 分为两个子任务。

## S4-A 条款逐条解读

基于：

Article + Requirement

逐条生成：

```text
第几条
原文
解读
监管要点
关联条款
```

---

## S4-B 整体法规解读

输出：

### 01 基本信息

### 02 出台背景

### 03 出台目的

### 04 法规定位

### 05 适用范围

### 06 整体架构

### 07 核心监管要求

### 08 尽职性要求

### 09 禁止及限制性要求

### 10 证据要求

### 11 程序及审批要求

### 12 报送及审计要求

### 13 关键数字与时间

### 14 实施及过渡期

### 15 逐条解读

并根据法规内容动态调整，不要求所有法规机械出现所有栏目。

---

# 十四、S4语言控制规则

这是一个独立的 Style Guardrail。

### 禁止默认出现：

```text
重大
全面
深刻
显著
极大
史上最严
里程碑
全面重塑
根本改变
前所未有
强力监管
重磅
颠覆
```

除非：

> 官方原文明确使用。

---

## 推荐表达

不写：

> 监管全面强化了核销管理。

写：

> 《办法》进一步明确了呆账认定、审批、核销后管理及责任追究要求。

不写：

> 此举极大提升金融机构风险管理水平。

写：

> 相关要求有助于统一呆账核销标准，并强化核销后的资产管理和责任管理。

---

# 十五、S5——版本比较

必须首先建立：

```text
current_version_id
direct_previous_version_id
historical_reference_version_ids
```

绝对不能将：

> 历史版本

自动当成：

> 直接前序版本。

---

## 输出

逐条差异矩阵：

| 当前条款 | 前版条款 | 变化类型 | 当前规定 | 前版规定 | 解读 |
|---|---|---|---|---|---|

变化类型固定：

```text
新增
删除
修订
明确
细化
扩围
缩围
收紧
放宽
程序调整
时限调整
阈值调整
表述调整
```

如果无法明确判断：

> “待人工判断”

不要硬分类。

---

# 十六、S6——内容编排与证据绑定

S6 **不创造新的监管事实**。

它只做三件事：

### 1. 组织

将 S1-S5 结果按照报告模板组合。

### 2. 绑定

每一个监管结论关联：

```text
article_id
requirement_id
evidence_id
```

### 3. 建立导航关系

例如：

```text
核心监管要求
↓
Requirement 001
↓
第十四条
↓
Article 014
↓
原文位置
```

---

# 十七、Evidence Object——证据对象

```json
{
  "evidence_id": "EVI_FIN_MOF_2017_90_014_001",

  "source_type": "regulation_original",

  "source_document_id": "FIN_MOF_2017_90",

  "article_id": "FIN_MOF_2017_90_ART_014",

  "source_text": "……",

  "page": 6,

  "location": {},

  "authority_level": 1
}
```

---

# 十八、证据等级

## L1

监管原文

## L2

监管机关官方解释

## L3

直接关联法规

## L4

研究机构、咨询机构、律师事务所

## L5

其他研究材料

原则：

> L4/L5 不可单独证明监管义务。

---

# 十九、QC Engine

QC 不应该只是一条 Reviewer Prompt。

建议设计为：

```text
Rule-based QC
+
LLM Reviewer
+
人工复核
```

---

# 二十、规则校验

系统程序直接检查：

### 数字

- 金额
- 百分比
- 日期
- 天数
- 月数
- 年数
- 次数

### 引用

Article ID 是否存在。

### 条款

关联条款是否存在。

### 版本

目标法规版本是否匹配。

### 完整性

是否存在原文但未生成条款对象。

这种检查不要交给 LLM。

---

# 二十一、LLM Reviewer

负责检查：

- 是否改变监管原意
- 是否遗漏重要限定词
- 是否忽视例外
- 解读是否过度
- 语言是否绝对化
- 是否将解读写成事实
- 是否存在无法从证据支持的判断

---

# 二十二、人工复核路由

建议设三档：

### Green

可以自动发布。

典型：

> 明确日期、明确义务、明确报送事项。

### Yellow

建议人工复核。

例如：

> 根据多条规则形成的监管含义。

### Red

必须人工复核。

例如：

- 法规冲突
- OCR疑似错误
- 原文存在歧义
- 历史版本缺失
- 官方材料存在差异
- Agent无法确定适用关系

---

# 二十三、统一 Workflow State

这是解决“页面之间断掉”的关键设计。

一项解读任务必须具有统一：

```text
task_id
```

例如：

```text
TASK_20260819_000001
```

其状态统一存储。

```json
{
  "task_id": "TASK_20260819_000001",

  "regulation_id": "FIN_MOF_2017_90",

  "current_step": "S4",

  "steps": {

    "S1": {
      "status": "completed",
      "version": 1
    },

    "S2": {
      "status": "completed",
      "version": 1
    },

    "S3": {
      "status": "completed",
      "version": 2
    },

    "S4": {
      "status": "running"
    },

    "S5": {
      "status": "pending"
    },

    "S6": {
      "status": "pending"
    }
  }
}
```

---

# 二十四、前端流程页面

建议左侧固定流程导航：

```text
① 上传材料

② 文件解析

③ 法规识别

④ 条款拆解

⑤ 外规解读

⑥ 新旧规比较

⑦ 质量校验

⑧ 最终结果
```

每个页面均读取：

> 同一个 task_id。

不能每页自己生成任务。

---

# 二十五、每一步都必须能查看

例如 S3 页面：

### 条款处理进度

```text
总条款：26
已解析：26
存在监管规则：23
仅定义/附则：3
```

点击：

> 第14条

展开：

```text
原文

↓

规则 1
规则 2
规则 3

↓

证据

↓

状态：已校验
```

这样用户真正能知道 Agent 做了什么。

---

# 二十六、HTML 最终页面设计

建议布局：

```text
┌────────────────────────────────────┐
│ 法规标题                           │
│ 发文机关｜文号｜发布日期｜实施日期 │
└────────────────────────────────────┘

┌───────────┬────────────────────────┐
│ 左侧目录   │ 主内容                  │
│           │                         │
│ 法规速览   │                         │
│ 背景目的   │                         │
│ 适用范围   │                         │
│ 核心要求   │                         │
│ 数字要求   │                         │
│ 新旧规比较 │                         │
│           │                         │
│ 逐条解读   │                         │
│  第1条     │                         │
│  第2条     │                         │
│  第3条     │                         │
└───────────┴────────────────────────┘
```

---

# 二十七、HTML导航不能依赖静态锚点

基础页面目录可以使用 HTML anchor 辅助。

但核心业务导航应使用：

```text
router
+
task_id
+
regulation_id
+
article_id
```

例如：

```text
/regulations/FIN_MOF_2017_90/articles/014
```

或者：

```text
/tasks/TASK_001/regulation/articles/014
```

而不是仅：

```text
#article14
```

---

# 二十八、条款跳转

点击：

> 第十四条

前端读取：

```text
article_id
```

然后定位 Article Object。

点击：

> 查看原文

定位：

```text
evidence_id
```

而不是根据文字：

> “第十四条”

重新搜索页面。

---

# 二十九、跨条款跳转

如果第14条解读引用第16条：

页面显示：

> 关联条款：第十六条

点击：

```text
related_article_id
↓
router
↓
Article 016
```

---

# 三十、返回路径

所有页面至少提供：

```text
返回上一位置
上一条
下一条
返回目录
```

用户点击关联条款后，必须能回到原来的解读位置。

建议保留：

```text
from_article_id
from_requirement_id
scroll_position
```

---

# 三十一、Word输出

Word不单独生成内容。

统一读取：

> Regulation Data Model。

建议结构：

```text
封面

1 法规概览
2 出台背景与监管目的
3 法规定位
4 适用范围
5 整体结构
6 核心监管要求
7 尽职性要求
8 禁止及限制性要求
9 关键数字及时间
10 新旧规主要变化
11 外规逐条解读
12 信息来源
```

---

# 三十二、Word逐条解读格式

### 第十四条

**外规原文**

原文……

**外规解读**

解读……

**监管要点**

……

**关联条款**

……

---

# 三十三、Word与HTML一致性控制

必须满足：

```text
同一 interpretation_id
```

在 Word 与 HTML 中：

> 内容完全一致。

不能：

HTML：

> 核销后仍需追索。

Word：

> 核销后原则上需要持续开展债权清收工作。

即使两句话语义接近，也不应由两个生成流程分别改写。

---

# 三十四、版本控制

任何人工修改不得直接覆盖。

例如：

```text
Interpretation v1
↓
人工修改
↓
Interpretation v2
```

保存：

```text
修改人
修改时间
修改前
修改后
修改原因
```

这样未来才具备：

> 审计追踪能力。

---

# 三十五、用户人工修改后的逻辑

这是网站开发中特别容易做错的一点。

如果用户修改：

> 第14条解读

系统不得重新运行 S4 后把用户修改覆盖掉。

应设置：

```text
AI Draft
Human Reviewed
Human Locked
```

`Human Locked` 内容只有人工明确解除锁定后才能被 AI 更新。

---

# 三十六、失败恢复机制

任何 Skill 失败都不能导致整个任务失效。

例如：

S4 处理到：

```text
第1—16条完成
第17条失败
```

系统必须保存 1—16 条。

重新运行：

> 从第17条继续。

而不是：

> 全部重新生成。

---

# 三十七、任务断点

所有节点要支持：

```text
Resume
Retry
Re-run selected item
```

这是平台型 Agent 和一次性聊天 Agent 的重要区别。

---

# 三十八、需要特别警惕的开发问题

## 风险 1

前端先做漂亮界面，后补数据结构。

**禁止。**

应该：

> 先 Data Model，再页面。

---

## 风险 2

大模型每次重新读取全部法规。

会造成：

- 结果漂移
- 成本高
- 速度慢
- 前后不一致

应该：

> 第一次结构化后，后续节点读取结构化对象。

---

## 风险 3

每个 Skill 输出 Markdown。

不建议。

Skill核心输出应为：

> JSON。

Markdown属于 Renderer。

---

## 风险 4

所有内容一次生成。

对于50—100条以上法规容易失败。

应该：

> 条款级批处理 + checkpoint。

---

## 风险 5

为了页面跳转，靠字符串匹配。

例如：

```text
find("第十四条")
```

长期一定出问题。

必须：

> ID-based navigation。

---

# 三十九、我建议的开发顺序

现在不要马上开发前端。

建议顺序：

### Phase 1

**确定完整 Data Schema**

先确认：

```text
Regulation
Article
Requirement
Interpretation
Evidence
Version
Task
QC
```

---

### Phase 2

写 S1-S3 Prompt。

先解决：

> “法规到底说了什么。”

---

### Phase 3

用《金融企业呆账核销管理办法》跑 S1-S3。

人工验收。

---

### Phase 4

写 S4 Prompt。

重点调：

> 逐条解读质量。

---

### Phase 5

写 S5。

---

### Phase 6

建立 S6 + QC。

---

### Phase 7

开发 HTML Renderer。

---

### Phase 8

开发 Word Renderer。

---

### Phase 9

做 Workflow / Router / 状态管理。

---

### Phase 10

再做 UI 美化。

---

# 四十、下一步

现在最值得做的不是继续扩架构，而是把开发真正需要的数据结构定死。

下一份规格我建议直接进入：

# 《外规解读 Agent Data Schema v1.0》

逐个定义：

```text
Regulation Schema
Article Schema
Requirement Schema
Interpretation Schema
Evidence Schema
Version Schema
Task Schema
QC Schema
```

每一个字段我会给出：

> 字段名称  
> 中文定义  
> 数据类型  
> 是否必填  
> 允许值  
> 来源  
> 哪个 Skill 写入  
> 哪个 Skill 可修改  
> 前端怎么使用  
> Word怎么使用  
> 校验规则  
> 示例值

**这个 Data Schema 一旦确定，后面的 Prompt、数据库、API、HTML跳转和 Word 输出才有共同底座。**

这一步我建议做得非常细，宁可现在多花时间，也不要在开发到一半再改底层数据结构。