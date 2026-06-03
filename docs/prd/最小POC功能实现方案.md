# 6\.1最小POC功能实现方案

# 环检智枢 EnviroNexus 第一阶段最小功能实现方案

## 一、项目定位

**环检智枢 EnviroNexus** 是面向环保检测业务的知识驱动型智能协作平台。

项目最终希望逐步支撑环保检测业务中的标准方法查询、任务单理解、采样要求提示、设备耗材辅助、排单辅助、质控提醒和业务流程智能化。

当前第一阶段先聚焦一个最小、清晰、可落地的闭环：

> 输入检测因子或简单问题，系统能够返回对应的标准方法、适用范围、关键要求和依据来源。
> 
> 

这一阶段不追求一次性做完整业务系统，而是先把环保检测标准方法知识服务做稳，为后续任务单解析、排单辅助和业务系统联动打基础。

---

## 二、项目名称与子项目划分

本项目统一使用长期项目名：

> **环检智枢 EnviroNexus**
> 
> 

当前采用三个子项目协同推进：

整体调用关系：

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YzYzNzA0Y2FhMDgxMzE3ZDAzMGNkMjk0MmQ0YzFjMmJfOWU3NDdiY2EzOTVhMGU5MDhhOWI3M2RlNTRhNDAzMGZfSUQ6NzY0NjM4OTUyMzI1NzI5ODExMF8xNzgwMzE0MzgwOjE3ODA0MDA3ODBfVjM)

这样拆分后，每个方向都可以独立开发、独立调试，同时通过接口契约保持整体协同。

---

## 三、当前阶段目标

当前阶段的目标是跑通下面这个最小闭环：

检测因子 / 用户问题

→ 因子识别与别名匹配

→ 查询 MethodCard 方法卡

→ 组装结构化回答

→ 附加依据来源

→ 后端返回

→ 前端展示

一句话说明：

> 先证明环保检测标准方法可以被结构化、被查询、被解释、被展示。
> 
> 

---

## 四、本阶段做什么

---

## 五、本阶段暂不做什么

---

## 六、首批建议覆盖的检测因子

第一阶段建议优先覆盖水和废水类高频因子。

后续可以根据实际任务单逐步扩展到废气、噪声、土壤等类别。

---

## 七、MethodCard 方法卡最小结构

MethodCard 可以理解为检测方法的结构化说明卡。

它不是替代标准全文，而是把演示和查询最需要的信息先结构化出来。

建议字段如下：

示例：

```JSON
{
  "schema_version": "method_card.v0.1",
  "card_id": "water_cod_hj828_2017",
  "card_version": 1,
  "identity": {
    "category": "水和废水",
    "factor": "化学需氧量",
    "aliases": ["COD", "CODcr", "化学需氧量"],
    "standard_code": "HJ 828-2017",
    "standard_name": "水质 化学需氧量的测定 重铬酸盐法",
    "method_name": "重铬酸盐法"
  },
  "applicability": {
    "sample_types": ["地表水", "生活污水", "工业废水"],
    "field_or_lab": "实验室分析",
    "scope_summary": "适用于地表水、生活污水和工业废水中化学需氧量的测定。"
  },
  "requirements": [
    {
      "type": "preservation",
      "title": "样品保存",
      "content": "按标准要求进行样品保存。",
      "required": true,
      "evidence_ids": ["ev_001"]
    }
  ],
  "answer_template": {
    "short_answer": "化学需氧量可采用 HJ 828-2017 重铬酸盐法测定。",
    "key_points": [
      "适用于地表水、生活污水和工业废水。",
      "样品保存和干扰项需按标准执行。"
    ]
  },
  "source_document": {
    "doc_id": "doc_hj828_2017",
    "source_type": "standard",
    "title": "水质 化学需氧量的测定 重铬酸盐法",
    "standard_code": "HJ 828-2017",
    "status": "active",
    "import_mode": "manual_stage_1"
  },
  "evidence_refs": [
    {
      "evidence_id": "ev_001",
      "field_path": "applicability.scope_summary",
      "evidence_role": "applicability_basis",
      "source_title": "HJ 828-2017",
      "section": "适用范围",
      "summary": "该标准说明了化学需氧量测定方法的适用范围。"
    }
  ],
  "governance": {
    "review_status": "approved",
    "answer_visibility": "enabled",
    "reviewer": "manual",
    "updated_at": "2026-06-01"
  },
  "change_log": [
    {
      "version": 1,
      "change_type": "created",
      "change_note": "第一阶段首版方法卡"
    }
  ],
  "extensions": {}
}
```

---

## 八、核心接口设计

### 因子查询接口

这是当前阶段的主接口，用于输入检测因子或问题，并返回可展示结果。

POST /api/v1/factors/query

请求示例：

```JSON
{
  "query": "COD 怎么测？"
}
响应示例：
{
  "api_version": "v1",
  "matched": true,
  "factor": "化学需氧量",
  "matched_alias": "COD",
  "card_id": "water_cod_hj828_2017",
  "answer": {
    "summary": "化学需氧量可采用 HJ 828-2017 重铬酸盐法测定。",
    "standard_code": "HJ 828-2017",
    "standard_name": "水质 化学需氧量的测定 重铬酸盐法",
    "method_name": "重铬酸盐法",
    "applicability": "适用于地表水、生活污水和工业废水。",
    "requirements": [
      {
        "type": "preservation",
        "title": "样品保存",
        "content": "按标准要求进行样品保存。"
      }
    ],
    "evidence_refs": [
      {
        "source_title": "HJ 828-2017",
        "section": "适用范围",
        "summary": "该标准说明了化学需氧量测定方法的适用范围。"
      }
    ]
  },
  "warnings": []
}
```

### 方法卡详情接口

用于已知 `card_id` 后查看完整方法卡详情。

GET /api/v1/method\-cards/\{card\_id\}

典型使用场景：

### 健康检查接口

用于判断服务是否正常。

GET /api/v1/health

### 未命中返回示例

```JSON
{
  "api_version": "v1",
  "matched": false,
  "factor": null,
  "answer": null,
  "warnings": [
    "当前知识库暂未收录该检测因子，请人工确认后再使用。"
  ]
}
```

---

## 九、三个子项目职责

### 1\. `enviro-nexus-web`

**定位：前端工作台**

当前阶段主要负责：

检测因子查询页面

结果卡片展示

依据来源展示

未命中提示

演示页面体验优化

建议目录：

```JSON
enviro-nexus-web/
  README.md
  package.json
  src/
    pages/
    components/
      FactorQueryPanel.tsx
      MethodCardResult.tsx
      EvidenceList.tsx
    api/
      knowledgeApi.ts
    mocks/
      factor-query.mock.json
```

### 2\. `enviro-nexus-api`

**定位：业务后端服务**

当前阶段主要负责：

接收前端请求

调用知识服务

统一返回格式

日志记录

异常处理

健康检查

建议目录：

```JSON
enviro-nexus-api/
  README.md
  pyproject.toml
  uv.lock
  app/
    main.py
    routes/
    services/
      knowledge_client.py
    schemas/
    config/
  tests/
```

### 3\. `enviro-nexus-knowledge`

**定位：知识服务**

当前阶段主要负责：

MethodCard Schema

方法卡数据

因子别名表

因子匹配

答案组装

依据追溯

知识查询接口

接口契约源头

建议目录：

```JSON
enviro-nexus-knowledge/
  README.md
  pyproject.toml
  uv.lock
  data/
    method_cards.json
    factor_aliases.json
    sample_queries.json
  docs/
    method-card-schema.md
    api-contract.md
    sample-request.json
    sample-response.json
  app/
    main.py
    models/
      method_card.py
      query.py
      response.py
    core/
      factor_matcher.py
      method_card_store.py
      answer_builder.py
      evidence_builder.py
  tests/
```

---

## 十、前期工程准备

### 仓库准备

三个仓库统一使用：

enviro\-nexus\-web

enviro\-nexus\-api

enviro\-nexus\-knowledge

仓库命名规范：

### 后端与知识服务包管理

`enviro-nexus-api` 和 `enviro-nexus-knowledge` 使用 **uv** 作为 Python 包管理工具。

基本规范：

### 前端工程准备

前端可使用团队熟悉的 React / Umi / Vite 技术栈。

第一阶段页面不追求复杂，只需要：

```JSON
输入框
查询按钮
结果卡片
依据列表
异常提示
```

### 接口契约准备

接口契约以 `enviro-nexus-knowledge` 中的文档为源头：

```JSON
enviro-nexus-knowledge/docs/api-contract.md
enviro-nexus-knowledge/docs/sample-request.json
enviro-nexus-knowledge/docs/sample-response.json
```

协作规则：

```JSON
先改契约，再改代码
新增字段默认 optional
不直接删除字段，先标记 deprecated
接口路径统一带 /api/v1
返回结果带 api_version
演示前冻结接口和数据
```

---

## 十一、Superpowers 开发规范

本项目建议使用 **Superpowers** 作为 AI 辅助开发流程规范。

这里的 Superpowers 不是业务运行依赖，而是开发协作方法，用来约束 AI 辅助编码时的流程。

### 使用原则

### 推荐开发流程

每个任务按下面流程推进：

理解任务

→ 明确输入输出

→ 确认影响范围

→ 写实现计划

→ 编码

→ 自测

→ 更新文档

→ 提交

### AI 辅助开发提示词建议

团队使用 AI 工具开发时，可以统一采用下面的提示方式：

请先阅读当前仓库 README、docs 中的接口契约和相关代码。

在动手前先输出实现计划。

不要扩大任务范围。

实现后给出验证命令。

如果发现接口契约和代码不一致，先指出问题，不要自行大改。

### 任务粒度规范

每个开发任务尽量控制在半天内可完成。

示例：

实现 factor\_aliases\.json 加载

实现 COD / 化学需氧量别名匹配

实现 /api/v1/health

实现 /api/v1/factors/query 基础返回

实现前端结果卡片

补充 5 条查询测试用例

不建议一个任务同时包含：

接口设计 \+ 后端实现 \+ 前端展示 \+ 数据整理 \+ 测试

---

## 十二、分支、提交和文档小规范

### 分支规范

建议：

```JSON
main
dev
feature/xxx
fix/xxx
docs/xxx
```

示例：

```JSON
feature/factor-query-api
feature/method-card-schema
feature/web-result-card
fix/unknown-factor-warning
docs/api-contract
```

### 提交信息规范

建议使用简单清晰的提交信息：

```JSON
feat: add factor query api
feat: add method card schema v0.1
fix: handle unknown factor query
docs: update api contract
test: add factor matcher tests
chore: init uv project
```

### README 规范

每个仓库 README 至少包含：

```JSON
项目说明
本仓库职责
本地启动方式
常用命令
默认端口
环境变量
联调说明
负责人或维护人
```

### 默认端口规范

### 环境变量规范

示例：

```Plain Text
KNOWLEDGE_SERVICE_BASE_URL=http://localhost:8000
API_SERVICE_BASE_URL=http://localhost:8080
```

### 联调规范

建议每天固定一次小联调：

```Plain Text
前端可以访问后端
后端可以访问知识服务
知识服务健康检查正常
固定 5 个演示问题可以跑通
```

---

## 十三、人员分工

---

## 十四、时间计划

### Day 0：项目和仓库准备

### Day 1：方法卡结构和样本数据

### Day 2：知识服务和接口初版

### Day 3：首批方法卡和联调

### Day 4：测试与修正

### Day 5：第一阶段演示版冻结

---

## 十五、测试重点

---

## 十六、验收标准

---

## 十七、演示问题建议

---

## 十八、风险与应对

---

## 十九、后续扩展方向

第一阶段跑通后，可以逐步扩展：

更多检测因子

→ 更多检测类别

→ 任务单检测内容批量识别

→ 标准方法自动辅助抽取

→ 设备耗材要求整理

→ 采样规则提示

→ 排单辅助

→ 资源冲突校验

→ 完整业务流程联动

---

## 二十、团队共识

这次第一阶段的关键不是一次性做大，而是先把一个小点做清楚、做稳定、做可演示。

我们先围绕：

检测因子

→ 方法卡

→ 结构化答案

→ 依据来源

→ 页面展示

建立一个最小闭环。

只要这个闭环验证通过，后续任务单解析、排单辅助、设备耗材匹配、采样要求提示，都可以在这个基础上继续迭代。

最终目标是：

> 用一个小而稳的第一阶段成果，证明环保检测知识可以被结构化、被查询、被解释、被演示，并为后续智能排单和业务系统建设打基础。
> 
> 



