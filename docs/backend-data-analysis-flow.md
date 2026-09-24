# 锐音场后端数据接入与分析判断流程

## 目标

小程序负责采集项目输入、上传资料和触发操作；后端负责保存证据链、计算财务结果、组织外部数据采集、调用本地大模型生成分析说明，并把最终结论拆成可核验的事实、假设、风险、门禁和负责人决策。

核心原则：

- 文件、外部网络数据和 AI 输出不能直接成为最终事实。
- 所有结论必须保留来源、采集时间、状态和人工核验入口。
- 小程序只调用 `app/` 后端 API，不在端侧实现业务计算。
- Token、OSS 密钥、第三方 API Key 不写入小程序源码。

## 总体闭环

```text
小程序输入/上传
  -> 后端创建项目与版本
  -> OSS 或外部数据任务登记
  -> 文件解析 / 外部采集 / AI 分析
  -> 写入 Evidence / Fact / Assumption / Risk / Gate
  -> 财务测算与盈亏平衡
  -> Agent 给出下一步建议
  -> 负责人核验事实、关闭门禁、确认决策
  -> 生成报告与受限分享
```

## 1. 项目输入流程

小程序先通过五步创建流程提交基础项目数据：

- 项目名称、类型、艺人、城市、场馆、档期
- 预估上座、平均票价、艺人费、场地费、宣发费、制作费

后端接口：

- `POST /projects`
- `GET /projects`
- `GET /projects/{project_id}`
- `POST /projects/{project_id}/versions`
- `GET /projects/{project_id}/versions`

后端行为：

- 创建 `Project`
- 同步创建 `ProjectVersion`
- 保存输入快照
- 每次重新评估生成新版本，不覆盖历史版本

## 2. OSS 文件上传预留流程

用于小程序上传合同、场馆确认函、审批材料、票务报表、结算单、图片或 `.docx/.pdf` 等资料。

### 2.1 初始化上传

小程序调用：

```http
POST /oss/uploads/initiate
```

请求字段：

- `project_id`
- `fact_id` 可选
- `file_name`
- `content_type`
- `evidence_type`
- `source`
- `metadata`

后端返回：

- `upload_id`
- `object_key`
- `upload_url`
- `method`
- `headers`
- `expires_in_seconds`

当前实现是 `local-placeholder`，不绑定具体云厂商。后续接真实 OSS 时，只替换上传 URL 签名逻辑，小程序契约不变。

### 2.2 完成上传

小程序上传文件成功后调用：

```http
POST /oss/uploads/{upload_id}/complete
```

请求字段：

- `file_url`
- `size`
- `checksum`
- `fact_id` 可选
- `metadata`

后端行为：

- 更新 `OSSUpload.status = completed`
- 写入 `file_url/object_key/size/checksum`
- 自动创建一条 `Evidence`
- `Evidence.status = uploaded`

当前已实现：上传登记与 Evidence 落库。

尚未实现：真实文件二进制存储、预签名 URL、下载签名。

## 3. 文件解析与证据分析流程

针对 `.docx`、`.pdf`、图片和表格类文件，统一进入异步解析任务，不为不同文件类型拆分业务流程。文件类型只影响解析器选择，不影响证据链、核验和决策口径。

```text
Evidence(uploaded)
  -> DocumentParseJob(queued)
  -> 按文件类型提取正文、表格、图片 OCR 或行列数据
  -> 结构化候选事实
  -> 写入 Fact / Assumption / Risk / Gate
  -> 标记为 needs_review
  -> 人工核验后变为 verified/rejected
```

建议新增接口：

- `POST /evidences/{evidence_id}/parse-jobs`
- `POST /document-parse-jobs/{job_id}/run`
- `POST /document-parse-jobs/{job_id}/confirm-projects`

当前已实现接口：

- `POST /evidences/{evidence_id}/parse-jobs`
- `POST /document-parse-jobs/{job_id}/run`
- `POST /document-parse-jobs/{job_id}/confirm-projects`

当前已实现真实解析：

- `.docx`：优先使用 `python-docx` 提取正文和表格；依赖不可用时使用 OpenXML 兜底读取正文。
- 文本型 `.pdf`：优先使用 `pdfplumber`，再回退 `pypdf`。
- `.xlsx/.csv`：使用 `openpyxl` 或 CSV 解析抽取 sheet、表头、行数据和候选项目。
- 单项目文档解析完成后写入候选 `Fact / Assumption / Risk / Gate`，状态分别保持 `pending / active / open / pending`。
- 表格批量导入解析后生成 `candidate_projects`、`field_mapping` 和预览数据，仍需用户确认后才创建项目。

解析器建议：

- `.docx`：使用 `python-docx` 提取正文和表格。
- 文本型 `.pdf`：使用 `pypdf` 或 `pdfplumber` 提取正文和表格。
- 扫描型 `.pdf`：先转图片，再接 OCR。
- 图片：OCR。
- `.xlsx/.xls/.csv`：表格解析，按 sheet、表头、行数据抽取候选项目或候选财务输入。

合同、审批、场馆函和项目说明类文件应抽取：

- 项目名称、艺人、城市、场馆、档期
- 场馆容量、可售座位、票价、费用、预算
- 审批、授权、付款、违约、责任条款
- 不确定项、冲突项和缺失资料

解析结果不能直接当事实，应先写为候选项：

- `Fact.status = pending`
- `Assumption.status = active`
- `Risk.status = open`
- `Gate.status = pending`

### 3.1 PDF 与 DOCX

PDF 和 DOCX 内容如果表达的是同一类合同、审批材料或项目说明，业务处理完全一致：

```text
PDF/DOCX Evidence
  -> DocumentParseJob(parse_scope=single_project)
  -> 候选 Facts / Assumptions / Risks / Gates
  -> 人工核验
  -> 进入财务和项目判断
```

PDF 的特殊点只在技术解析：

- 可复制文字的 PDF 走文本和表格解析。
- 扫描件 PDF 走 OCR。
- 解析失败时仍保留 Evidence，并生成“资料解析失败/需人工录入”的任务。

### 3.2 Excel / CSV 批量项目

Excel 或 CSV 可以一次包含多个项目、多个城市站点或多个候选方案。推荐流程：

```text
Spreadsheet Evidence
  -> DocumentParseJob(parse_scope=batch_projects)
  -> 解析 sheet、表头和行
  -> 生成 candidate_projects
  -> 小程序展示字段映射和数据预览
  -> 用户确认
  -> confirm-projects 批量创建 Project + ProjectVersion
  -> 每个 Project 独立测算、风险、门禁和结论
```

字段映射应支持同义表头：

- 艺人 / Artist / 嘉宾
- 城市 / 站点 / 地区
- 场馆 / Venue
- 日期 / 档期
- 预计人数 / 容量 / 上座
- 平均票价 / 票价
- 艺人费 / 出场费
- 场租 / 场地成本
- 宣发费 / 投放预算
- 制作费 / 舞美搭建

Excel 解析后不应直接创建正式项目。必须先生成候选项目并展示给用户确认。确认后，每条候选项目独立创建：

- `Project`
- 初始 `ProjectVersion`
- 可选财务测算任务
- 可选分析任务

巡演场景下，批量项目还应支持汇总报告：

- 推荐推进排序
- 城市/站点利润对比
- 资金缺口对比
- 高风险站点列表
- 缺失资料清单

## 4. 外部数据异步采集流程

用于获取 Web、第三方 API、Skill、MCP 或内部数据服务的信息，例如艺人热度、舆情、同档期竞争、城市消费、票务趋势等。

后端接口：

- `POST /external-data/jobs`
- `GET /external-data/jobs`
- `GET /external-data/jobs/{job_id}`
- `POST /external-data/jobs/{job_id}/run`

任务字段：

- `project_id`
- `source_type`: `web` / `api` / `skill` / `mcp`
- `provider`
- `query`
- `purpose`
- `parameters`

当前实现：

- 创建 `ExternalDataJob`
- 状态从 `queued` 到 `completed`
- 返回占位结果
- 明确标注 `requires_human_verification = true`

后续真实接入时：

- `web`: 搜索、新闻、公开网页、舆情摘要
- `api`: 票务、热度、城市、场馆、天气、交通
- `skill`: 大模型 Skill 编排的数据分析
- `mcp`: 浏览器、文档、内部知识库、外部工具

外部数据入库要求：

- 保存来源 URL/API 名称
- 保存采集时间
- 保存原始片段或摘要
- 保存置信度
- 保存是否需要人工核验
- 禁止把不可追溯数据直接写为 verified fact

## 5. 财务测算流程

后端接口：

- `POST /finance/calculate`
- `POST /finance/breakeven`

输入来源：

- 小程序人工输入
- 文档解析出的候选数据
- 已核验事实
- 项目版本历史

后端输出：

- 三种情景：保守、中性、乐观
- 收入、成本、利润
- 保本人数
- 缺失字段
- 公式版本
- 新 `ProjectVersion`

规则：

- 缺失字段不能按 0 计算。
- 每次测算保留版本。
- 财务结果是确定性计算，不依赖大模型。

## 6. AI 分析与 Agent 建议流程

当前 AI 能力：

- `/ai/generate` 调用本地 `llama_server`
- 关闭 Qwen thinking 模式，避免返回推理过程
- 超时 300 秒
- 不允许编造日期、票价、技术参数、效果数字

Agent 能力：

- `POST /agent/chat`
- 基于项目状态、风险和门禁给出下一步建议

已新增“项目分析结论”专用接口：

- `POST /projects/{project_id}/analysis-jobs`
- `GET /projects/{project_id}/analysis-jobs/{job_id}`

分析输入：

- 项目版本
- 财务测算结果
- 已核验 Facts
- 未核验 Assumptions
- Risks
- Gates
- Evidence 摘要
- ExternalDataJob 结果

AI 输出不能直接落最终决策，应拆成：

- 分析说明
- 风险解释
- 缺失资料建议
- 需要人工确认的问题
- 推荐动作：推进 / 调整后推进 / 暂缓 / 不建议推进

## 7. 人工核验与最终判断

最终判断必须经过负责人确认。

后端接口：

- `POST /facts/{fact_id}/verify`
- `POST /gates`
- `POST /risks`
- `POST /decisions`
- `POST /reports/{project_id}/share`

状态口径：

- `Fact`: `pending` / `verified` / `rejected` / `needs_review`
- `Gate`: `pending` / `confirmed` / `blocked`
- `Risk`: `open` / `mitigated` / `closed`
- `Project`: `draft` / `calculated` / `pending_confirmation` / `archived`

最终判断示例：

- `advance`: 可以推进
- `conditional_advance`: 调整后推进
- `pause`: 暂缓
- `reject`: 不建议推进

决策要求：

- 关联 `project_id`
- 关联 `version_id`
- 保存 `conditions`
- 保存负责人
- 保存时间
- 不覆盖历史决策记录

## 8. 小程序端职责

小程序负责：

- 登录和客户空间选择
- 创建项目
- 上传文件
- 查看证据、事实、风险、门禁
- 发起外部数据采集任务
- 发起测算和报告分享
- 提交任务结果
- 展示 AI 建议和人工确认入口

小程序不负责：

- 直接持有 OSS 密钥
- 直接访问第三方 API Key
- 直接计算财务模型
- 把 AI 输出当最终事实
- 绕过后端权限读取文件

## 9. 当前已完成能力

已实现：

- 项目、版本、财务、盈亏平衡
- Facts / Evidences / Assumptions / Risks / Gates
- Tasks / Decisions / Reports
- OSS 上传预留接口
- ExternalDataJob 异步采集预留接口
- DocumentParseJob 文档解析接口
- DOCX / PDF / XLSX / CSV 解析器
- 解析结果自动写入候选事实、假设、风险和门禁
- Excel 候选项目批量确认接口
- ProjectAnalysisJob 项目分析任务
- 本地 llama_server 宣发生成
- 小程序 API 封装

未实现但已预留：

- 真实 OSS 预签名上传
- OCR
- 外部 Web/API/Skill/MCP 真实采集执行器
- 分析结果直接驱动负责人最终决策流转

## 10. 推荐下一步

优先级建议：

1. 小程序在证据上传完成后展示“开始解析资料”和“生成分析结论”操作入口。
2. 为 Excel 字段映射确认补充独立页面，允许用户在确认前调整表头映射。
3. 接入 OCR 处理扫描 PDF 和图片资料。
4. 接入真实 OSS 预签名上传与下载签名。
5. 接入真实外部 Web/API/Skill/MCP 数据采集执行器。
