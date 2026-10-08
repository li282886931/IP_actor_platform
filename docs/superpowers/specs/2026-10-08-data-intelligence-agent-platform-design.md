# 数据情报与项目专属工作平台设计

## 目标

在现有项目、财务、证据、风险、任务和复盘能力之上，建设可落地的数据资产与决策中台：

- 将主办方资料、平台数据、行业案例和后续授权外部数据统一为可追溯资产。
- 为艺人动态、舆情、档期、地域、场馆、售票和资金变化提供持续预警。
- 为每个项目建立持续运行的工作计划、项目记忆、任务编排与人工门禁。
- 将实际售票、结算和复盘结果沉淀为案例与预测校准数据。
- 对接第三方 API、MCP、Skill 或合规数据服务时，只通过可配置连接器执行；本轮不内置未授权抓取。

## 约束

- 所有业务数据必须有来源、采集时间、租户、可见范围、状态和使用权限。
- 真实观测、历史案例、人工假设、模型估计必须分开存储与展示。
- 转化率或“想看人数”不能写死为固定乘数；必须使用版本化参数和来源说明。
- 财务公式、审批门槛、合同权限、资金拨付和租户边界不可由模型自动修改。
- 每个项目工作只可创建预定义任务类型；高风险动作仍由具名负责人确认。
- 外部连接器默认处于 `configured` 或 `disabled`，没有凭据或授权时不得发起网络请求。
- 所有新增内容需要后端、Taro 和原生微信生成器测试。

## 现有能力复用

- `Evidence`、`Fact`、`Assumption`、`Risk`、`Gate`：项目证据链和人工核验。
- `ExternalDataJob`：外部数据需求和异步执行入口。
- `Task`、`ProjectAnalysisJob`：人工任务和项目分析任务。
- `ProjectVersion`、`TicketingSnapshot`、`ProjectActual`：预测、售票、结算和复盘。
- `Notification`：站内提醒，扩展为预警投递终点。
- `Artist.profile`、`Venue`、`TourPlan`、`TourStop`：艺人、场馆、地域和档期基础实体。

## 新增领域模型

### 数据资产

#### DataSource

描述可被使用的数据来源，不存储明文凭据。

- `tenant_id`：来源所属租户，平台公共来源使用系统租户。
- `name`、`source_kind`：主办方文件、平台指标、授权 API、人工维护、行业案例。
- `connector_key`：适配器标识，如 `ticketing_api`、`artist_monitor`、`venue_registry`。
- `status`：`configured`、`disabled`、`active`、`error`。
- `credential_ref`：外部密钥管理系统的引用，不保存 AK/SK。
- `schedule_config`：轮询周期、时区、允许窗口。
- `scope_config`：可读取的艺人、城市、项目或指标范围。

#### DataAsset

表示一个原始资料、API 响应批次或人工录入版本。

- `tenant_id`、`project_id`、`data_source_id`。
- `asset_type`：函件、合同、财务表、艺人动态、舆情、档期、地域、票房、案例。
- `source_uri`、`content_hash`、`captured_at`、`effective_until`。
- `visibility`：`tenant`、`project`、`restricted`。
- `status`：`received`、`parsed`、`needs_review`、`verified`、`expired`、`rejected`。
- `raw_payload_ref`：对象存储原始文件或响应位置。

#### DataRecord

标准化可查询记录，保留字段级来源。

- `asset_id`、`entity_type`、`entity_id`、`metric_key`。
- `value_json`、`unit`、`observed_at`、`confidence`。
- `record_status`：`observed`、`estimated`、`assumed`、`verified`、`conflicted`。
- `lineage`：来源字段、解析器版本、人工核验人。

#### DataQualityIssue

记录重复、冲突、过期、缺字段、异常波动等问题。

- `asset_id`、`record_id`、`issue_type`、`severity`。
- `details`、`status`、`resolved_by`、`resolved_at`。

### 监控与预警

#### MonitoringRule

版本化规则，作用域可为艺人、项目、城市、场馆或巡演。

- `rule_type`：舆情、档期冲突、地域、场馆、票房、资金、资料过期、政策。
- `condition_json`：指标阈值、比较窗口、目标范围。
- `severity_policy`：提醒、重要、紧急。
- `notification_policy`：负责人、项目成员、财务、运营。
- `enabled`、`version`。

#### AlertEvent

由数据变更或定时检查触发，具有幂等业务键。

- `tenant_id`、`project_id`、`rule_id`、`business_key`。
- `severity`、`title`、`summary`、`context`。
- `status`：`open`、`acknowledged`、`resolved`、`suppressed`。
- `source_record_ids`、`dedupe_key`、`triggered_at`、`resolved_at`。

预警创建后：

1. 写入 `AlertEvent`。
2. 幂等创建或更新 `Notification`。
3. 对需要行动的预警创建预定义 `Task`。
4. 触发项目决策快照重新计算。

### 决策、案例与校准

#### DecisionSnapshot

为项目建立不可变决策快照，聚合实际事实、有效假设和财务结果。

- `project_id`、`project_version_id`、`snapshot_type`。
- `input_lineage`：使用到的 `DataRecord`、`Evidence`、`Fact`、`Assumption` ID。
- `finance_result`、`risk_summary`、`alert_summary`、`recommendation`。
- `created_by_type`：系统、人工、工作流。

#### ConversionAssumption

管理曝光、想看、预约、购票、到场转换参数。

- `tenant_id`、`scope_type`、`scope_id`。
- `funnel_stage_from`、`funnel_stage_to`、`rate`。
- `segment`：艺人类型、城市层级、票价区间、渠道、时间窗口。
- `evidence_ids`、`confidence`、`status`、`effective_from`、`effective_until`。

任何“想看人数 × 转化率”的计算必须引用 `ConversionAssumption` 的版本和来源；无有效参数时返回待补齐，而不是默认使用常数。

#### CaseOutcome 与 ForecastCalibration

- `CaseOutcome`：成功/失败案例标签、场景、收入、成本、利润、上座率、失败原因、证据来源。
- `ForecastCalibration`：预测指标、实际指标、误差、适用人群、城市、场馆和参数版本。

复盘完成后只生成校准候选，必须人工审核才可影响新的 `ConversionAssumption`。

### 项目专属工作

#### ProjectWorkPlan

每个项目一份当前计划及其版本。

- `project_id`、`version_no`、`status`。
- `plan_json`：目标、约束、预定义任务、依赖关系、升级策略。
- `decision_snapshot_id`、`created_from_event_id`。

#### ProjectWorkEvent

持久化项目变化和工作流推进过程。

- `project_id`、`event_type`、`business_key`、`payload`。
- `source_asset_id`、`alert_event_id`、`decision_snapshot_id`。
- `status`、`processed_at`、`idempotency_key`。

项目工作循环：

1. 数据接入或人工录入产生事件。
2. 校验数据质量和来源权限。
3. 匹配预警规则并生成预警。
4. 生成新的决策快照。
5. 比较上一快照，仅对实质变化更新工作计划。
6. 创建、更新或关闭预定义任务。
7. 等待人工任务、补充证据或审批。
8. 根据结果重算并记录工作事件。

## 连接器框架

### 适配器协议

每个连接器实现以下受控方法：

- `validate_config(config)`：检查配置引用和作用域，不读取密钥明文。
- `fetch(request)`：仅在 `DataSource.status = active` 且存在授权配置时执行。
- `normalize(raw)`：转换为 `DataAsset` 和 `DataRecord`。
- `health_check()`：返回连接状态、最近成功时间和错误摘要。

首批预留连接器：

- `artist_monitor`：艺人公开动态、舆情指标、公开档期。
- `venue_registry`：场馆容量、报价、消防、交通和档期。
- `regional_market`：地域消费、竞品活动、节假日和政策。
- `ticketing_api`：曝光、想看、预约、购票、退票、售票快照。
- `organizer_files`：主办方函件、合同、财务表、执行记录。
- `industry_case_import`：成功/失败案例和市场报告。

本轮实现：

- 数据源登记、适配器注册、请求校验、运行记录和健康状态。
- `ExternalDataJob` 迁移为适配器执行任务的兼容入口。
- 无真实连接器凭据时返回 `configured/disabled` 状态和明确原因。

本轮不实现：

- 未授权网站抓取。
- 明文密钥存储。
- 生产第三方账号或支付/合同操作。

## 服务器组件

```text
Miniapp / 管理台
        |
API Gateway + Tenant Context + RBAC
        |
Decision API
├─ Project / Finance Service
├─ Data Asset Service
├─ Monitoring & Alert Service
├─ Project Work Service
├─ Case & Calibration Service
└─ Connector Gateway
        |
Async Worker / Scheduler
├─ connector fetch
├─ document parsing
├─ data quality checks
├─ alert evaluation
├─ work-plan refresh
└─ calibration candidate generation
        |
MySQL + Object Storage + Redis
```

- MySQL：业务实体、资产索引、规则、预警、工作流、快照和校准。
- 对象存储：原始函件、合同、表格、API 原始响应和解析产物。
- Redis：幂等键、调度锁、任务去重、预警冷却窗口和短期缓存。
- Worker：使用应用内可测试执行器抽象；生产部署可替换为队列消费者。
- Scheduler：执行数据新鲜度检查、规则扫描和已配置数据源同步。

## API 设计

### 数据资产

- `POST /data-sources`
- `GET /data-sources`
- `POST /data-sources/{id}/health-check`
- `POST /data-assets`
- `GET /data-assets?project_id=&asset_type=&status=`
- `GET /data-records?entity_type=&entity_id=&metric_key=`
- `POST /data-quality-issues/{id}/resolve`

### 预警与工作

- `POST /monitoring-rules`
- `GET /monitoring-rules`
- `GET /alerts?project_id=&status=&severity=`
- `POST /alerts/{id}/acknowledge`
- `POST /alerts/{id}/resolve`
- `POST /projects/{id}/work-events`
- `GET /projects/{id}/work-plan`
- `POST /projects/{id}/work-plan/refresh`
- `GET /projects/{id}/decision-snapshots`

### 转化、案例与校准

- `POST /conversion-assumptions`
- `GET /conversion-assumptions?scope_type=&scope_id=`
- `POST /case-outcomes`
- `GET /case-outcomes?artist_id=&city=&venue_id=`
- `GET /projects/{id}/calibration`
- `POST /calibration-candidates/{id}/approve`

所有接口沿用 `{"code": 0, "data": ...}` 包装、租户上下文和 Pydantic v2 序列化模式。

## 小程序与管理台

### 小程序

- S20 艺人详情：动态、画像、风险、档期、转化参数、来源状态。
- S22-S24 城市/日期/场馆：地域指标、竞品、政策、场馆变化和预警。
- S11/S25：决策快照、转化假设来源、预警影响、案例参考。
- S52/S53：项目专属工作计划、变化事件、预警和任务推进。
- S64-S66：售票漏斗、结算、案例沉淀和校准候选。

### 管理台

- 数据来源管理：来源状态、授权范围、健康检查和同步记录。
- 资产核验：资料解析、字段冲突、人工确认和可见范围。
- 预警规则：阈值、接收人、冷却窗口、启停和版本。
- 案例与校准：结果录入、误差审核、参数发布。

## 研发切片

### 切片一：数据资产与来源治理

实现 `DataSource`、`DataAsset`、`DataRecord`、`DataQualityIssue`，建立对象存储引用、来源血缘、人工核验和连接器注册框架。

### 切片二：艺人/地域/档期监控与预警

实现 `MonitoringRule`、`AlertEvent`、定时扫描、通知幂等写入和任务派发。预置规则仅针对已录入数据和模拟适配器结果。

### 切片三：项目专属工作与决策快照

实现 `DecisionSnapshot`、`ProjectWorkPlan`、`ProjectWorkEvent`、事件驱动重算、计划版本和人工门禁。

### 切片四：转化、案例与校准

实现 `ConversionAssumption`、`CaseOutcome`、`ForecastCalibration`、人工审核和决策引用。

### 切片五：多端展示与运维

扩展小程序聚合页面、原生微信生成器、管理接口、调度运行状态、可观测性和回归测试。

## 测试与验收

- 每个新增模型都有租户隔离、幂等和状态机测试。
- 每个连接器都有配置校验、禁用状态、无凭据阻断、标准化和来源血缘测试。
- 预警测试覆盖触发、去重、冷却、确认、解决、任务创建和通知写入。
- 工作流测试覆盖事件幂等、计划版本、实质变化判断、任务升级和人工阻塞。
- 转化测试覆盖参数来源、有效期、缺参阻断、人工审核和校准候选。
- 小程序与原生微信测试覆盖艺人情报、地域预警、项目工作和复盘校准展示。
- 所有外部连接器在没有授权配置时不执行网络调用。
- `git diff --check`、后端 pytest、Taro Vitest 和原生 Node 测试全部通过。
