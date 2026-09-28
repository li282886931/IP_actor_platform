# 微信小程序 84 页真实数据聚合层实施计划

> 依据：`docs/superpowers/specs/2026-09-28-miniapp-screen-aggregation-design.md`

## 目标

在保留现有领域写接口的前提下，新增 `GET /miniapp/screens/{screen_id}` 页面数据聚合层，使 S01-S84 统一读取真实业务数据；删除小程序源码和原生 runtime 的 fixtures/示例回退，统一空状态、错误状态和模糊搜索选择行为。

## 实施约束

- 全程使用 TDD：每项行为先新增测试并确认按预期失败，再写最小实现。
- 不回退或覆盖当前工作区已有改动；每个切片开始前重新读取目标文件和 `git diff`。
- 后端 Pydantic 输出使用 `model_validate(...).model_dump()`。
- API 响应继续使用 `{"code": 0, "data": ..., "message": "ok"}`。
- 财务缺参时返回缺失字段，不生成模拟金额。
- 所有项目级查询按租户约束；不得使用默认项目 ID `1`。
- 新增初始化记录必须有稳定业务唯一键并幂等写入。
- `dist` 只由构建或生成脚本更新，不手工维护业务逻辑。

## 验证命令

```bash
python3 -m pytest tests/test_miniapp_screens.py -q
python3 -m pytest tests/test_main.py tests/test_miniapp_screens.py -q
cd ip_actor_wechat && npm run test:unit
cd ip_actor_wechat && npm run build:weapp
cd ip_actor_wechat && node tests/blueprint.test.mjs
```

若项目当前未安装 Node 依赖，先在 `ip_actor_wechat` 执行 `npm install`。新增测试依赖后提交 `package-lock.json`。

---

## 切片 0：保护当前基线

### 任务 0.1：记录并验证现有未提交功能

**只读检查：**

- `git status --short`
- `git diff -- app/models.py app/routes.py app/schemas.py app/services.py`
- `git diff -- ip_actor_wechat/src ip_actor_wechat/tools ip_actor_wechat/tests`

**执行：**

1. 运行当前后端和小程序测试，记录既有失败。
2. 确认微信登录 Mock、项目创建、模糊搜索和任务批处理改动均保留。
3. 后续提交只暂存本切片明确列出的文件。

**验收：**

- 能区分实施前既有失败与新回归。
- 不清理、不覆盖用户当前工作区。

---

## 切片 1：聚合契约、注册表与测试基座

### 任务 1.1：增加后端响应模型

**文件：**

- 修改 `app/schemas.py`
- 新增 `tests/test_miniapp_screens.py`

**RED：**

1. 测试 `MiniappScreenData` 可序列化 `summary/items/options/context/empty_state`。
2. 测试 `screen_id` 非 S01-S84 时校验失败。
3. 测试可选值保持 `None`，不自动转换为 `0` 或空字符串。

运行：

```bash
python3 -m pytest tests/test_miniapp_screens.py -q
```

预期：因模型尚不存在而失败。

**GREEN：**

- 新增 `MiniappScreenSummary`、`MiniappScreenItem`、`MiniappScreenAction`、`MiniappEmptyState`、`MiniappScreenContext`、`MiniappScreenData`。
- 使用 Pydantic v2 `ConfigDict` 和 `Field(default_factory=...)`。

### 任务 1.2：增加完整 provider 注册表

**文件：**

- 新增 `app/miniapp_screens.py`
- 修改 `tests/test_miniapp_screens.py`

**RED：**

1. 测试 `SCREEN_PROVIDERS` 键集合严格等于 S01-S84。
2. 测试每页有显式 `provider_key`、`required_context` 和 `domain`。
3. 测试未知 screen 不会落入默认 provider。

**GREEN：**

- 定义 `ScreenRequestContext`。
- 定义 84 页注册元数据。
- 首次实现只返回无业务数据的结构化空状态，后续切片逐域替换 provider。

### 任务 1.3：建立当前用户与租户请求上下文

**文件：**

- 修改 `app/services.py`
- 修改 `app/routes.py`
- 修改 `tests/test_miniapp_screens.py`

**RED：**

1. 登录 token 能解析到真实 `user_id` 和登录时租户。
2. `X-Tenant-Id` 只能选择当前用户具有 `TenantMember` 关系的租户。
3. token 缺失或无效返回 401，非成员租户返回 403。
4. 切换租户后返回的 token 保留当前用户身份。
5. 聚合 provider 不调用 `get_or_create_default_context` 隐式创建用户或成员。
6. 仅 S01、S04、S06-S09 允许匿名读取公开字段；其他 screen 必须有有效会话。健康检查继续使用现有 `/ping`。

**GREEN：**

- 新增 `resolve_request_context` FastAPI dependency。
- 兼容当前登录 token 契约，同时将 token 解析和成员校验集中到一个边界。
- 聚合路由全部使用解析后的 `user/tenant`，不信任查询参数中的租户 ID。

### 任务 1.4：增加聚合路由

**文件：**

- 修改 `app/routes.py`
- 修改 `tests/test_miniapp_screens.py`

**RED：**

1. 携带有效登录 token 调用 `GET /miniapp/screens/S10` 返回统一包装和响应字段。
2. `GET /miniapp/screens/S85` 返回 400。
3. 缺少页面必需上下文返回 422。
4. 请求中的 `project_id/version_id/task_id/artist_id/keyword` 正确传入 provider。

**GREEN：**

- 路由只调用 `build_miniapp_screen(...)`。
- 输出使用 `MiniappScreenData.model_validate(...).model_dump()`。
- 不在 `routes.py` 添加页面业务分支。

**切片验收：**

```bash
python3 -m pytest tests/test_miniapp_screens.py -q
python3 -m pytest tests/test_main.py tests/test_miniapp_screens.py -q
```

建议提交：`feat(api): add miniapp screen aggregation contract`

---

## 切片 2：项目、财务、依据与决策主链路（S10-S51）

### 任务 2.1：项目与版本 provider（S10-S18）

**文件：**

- 修改 `app/miniapp_screens.py`
- 修改 `tests/test_miniapp_screens.py`

**RED：**

1. S10 仅返回当前租户项目，`highlight` 等于真实进行中数量。
2. S10 无项目时 `items=[]` 且返回创建项目空状态。
3. S11 使用真实 `project_id`，不存在时 404，缺失时 422。
4. S12 返回真实版本顺序和当前版本 ID。
5. S13-S17 返回表单所需真实选项和已保存草稿上下文。
6. S18 只返回当前用户、当前租户的草稿。
7. 跨租户项目不能通过 ID 读取。

**GREEN：**

- 增加项目查询、版本摘要和创建上下文 helper。
- 去除 provider 内任何固定项目名、固定数量和固定金额。

### 任务 2.2：财务 provider（S25-S33）

**文件：**

- 修改 `app/models.py`
- 修改 `app/schema.sql`
- 修改 `app/schemas.py`
- 修改 `app/services.py`
- 修改 `app/miniapp_screens.py`
- 修改 `tests/test_miniapp_screens.py`

**RED：**

1. 项目可保存 `available_funds`、`venue_capacity`、票档及三种情景上座率，兼容旧请求。
2. S25-S30 从当前 `ProjectVersion.finance_result` 返回三情景。
3. S26 的票价结构来自已保存票档；无票档时只展示缺失状态。
4. S31 保本人数由真实总成本和票价计算。
5. S32 敏感性只改变上座率，结果可复算。
6. S33 资金缺口由 `max(total_cost - available_funds, 0)` 计算。
7. 任一必需参数缺失时不返回金额，并列出 `missing_fields`。

**GREEN：**

- 为 `Project` 增加可用资金、场馆容量、票档和情景上座率字段，同步 Pydantic、序列化、SQL DDL 与运行时补列逻辑。
- 复用 `calculate_finance_result` 和 `calculate_breakeven_result`。
- 将财务展示转换限制在后端 provider 内。

### 任务 2.3：依据、风险、门禁、决策和报告 provider（S34-S51）

**文件：**

- 修改 `app/miniapp_screens.py`
- 修改 `tests/test_miniapp_screens.py`

**RED：**

1. S34-S35 的判断摘要由当前版本、门禁、风险和最近决策组成。
2. S36-S42 分别读取假设、事实、证据、解析结果、缺口和冲突。
3. S43-S46 读取真实风险和门禁，并按严重级别/状态排序。
4. S47-S48 读取最近决策及其具名负责人。
5. S49 对比两个真实版本；不足两个版本时返回空状态。
6. S50-S51 读取报告证据和有效分享记录，不生成虚假报告状态。

**GREEN：**

- 新增批量查询 helper，避免每个 item 再查数据库。
- 所有 entity ID 和导航上下文写入响应 item。

**切片验收：**

```bash
python3 -m pytest tests/test_miniapp_screens.py -q -k "project or finance or evidence or decision"
python3 -m pytest tests/test_main.py tests/test_miniapp_screens.py -q
```

建议提交：`feat(api): aggregate project decision screens`

---

## 切片 3：任务与 Agent（S52-S60）

### 任务 3.1：任务 provider

**文件：**

- 修改 `app/miniapp_screens.py`
- 修改 `tests/test_miniapp_screens.py`

**RED：**

1. S55 只返回当前租户可访问任务并附真实项目名。
2. S56 返回可接、已选上下文所需字段，不默认选择任务 ID `1`。
3. S57/S58 要求有效 `task_id`，且任务必须属于当前租户。
4. 拒绝原因、附件数量、负责人和截止日期来自数据库。

**GREEN：**

- 复用 `serialize_task`。
- provider 不执行接受、拒绝或提交动作。

### 任务 3.2：Agent provider

**文件：**

- 修改 `app/miniapp_screens.py`
- 修改 `tests/test_miniapp_screens.py`

**RED：**

1. S52/S53 从任务和 `ProjectAnalysisJob` 聚合今日工作及计划。
2. S54 返回当前项目上下文和最近分析结果。
3. S59 仅在版本或关键输入确有变化时返回提醒。
4. S60 返回当前用户真实 Agent 权限；数据未建模时先返回空状态。

**GREEN：**

- 只从已有任务、版本和分析任务生成确定性摘要。
- Agent 权限留待切片 6 补表后替换空 provider。

**切片验收：**

```bash
python3 -m pytest tests/test_miniapp_screens.py -q -k "task or agent"
python3 -m pytest tests/test_main.py tests/test_miniapp_screens.py -q
```

建议提交：`feat(api): aggregate task and agent screens`

---

## 切片 4：前端统一加载层与真实状态

### 任务 4.1：建立前端单元测试环境

**文件：**

- 修改 `ip_actor_wechat/package.json`
- 新增 `ip_actor_wechat/vitest.config.ts`
- 新增 `ip_actor_wechat/src/test/setup.ts`
- 新增或更新 `ip_actor_wechat/package-lock.json`

**测试基座：**

1. 增加 Vitest、jsdom、React Testing Library 和 `test:unit` 脚本。
2. 提供 Taro API 的最小测试替身。
3. 运行空测试集，确认 runner、路径别名和 JSX 转换正常。
4. 随后的每个生产行为继续严格执行 RED-GREEN；测试工具配置本身不作为业务行为。

### 任务 4.2：新增页面数据客户端和类型

**文件：**

- 修改 `ip_actor_wechat/src/services/api.ts`
- 修改 `ip_actor_wechat/src/types/domain.ts`
- 新增 `ip_actor_wechat/src/services/screenData.test.ts`

**RED：**

1. `getMiniappScreen` 生成 `/miniapp/screens/S11?project_id=...`。
2. 未定义上下文参数不进入 URL。
3. 响应字段完整映射，不补造 item。
4. 401/403/409/422 保留可识别错误代码。

**GREEN：**

- 新增 `MiniappScreenData` 等 TypeScript 类型。
- 将 HTTP 错误归一化为 `ApiError`。

### 任务 4.3：改造 `BlueprintScreen` 加载状态

**文件：**

- 修改 `ip_actor_wechat/src/components/BlueprintScreen/index.tsx`
- 修改 `ip_actor_wechat/src/components/BlueprintScreen/index.module.scss`
- 新增 `ip_actor_wechat/src/components/BlueprintScreen/index.test.tsx`

**RED：**

1. 所有页面只发起一次 screen 聚合读取请求。
2. 切换页面先清空旧 items。
3. 空数据渲染服务端 `empty_state`。
4. 网络失败显示错误和重试，不显示 fixtures。
5. 401/403/409/422 分别进入 S81/S77/S78/上下文提示。
6. 动态标题、关键值和数量来自 response，而非 `screenDefinitions`。

**GREEN：**

- 删除 `fetchRemote` 中的领域读取 `switch`。
- 状态改为 `idle/loading/success/empty/error`。
- 保留现有领域写操作分支，成功后刷新聚合数据。

### 任务 4.4：建立 84 页前端映射

**文件：**

- 新增 `ip_actor_wechat/src/data/screenDataMap.ts`
- 修改 `ip_actor_wechat/src/data/screens.ts`
- 修改 `ip_actor_wechat/tests/blueprint.test.mjs`

**RED：**

1. S01-S84 每页都声明 `requiredContext` 和 `writeActions`。
2. 不允许默认 screen 映射。
3. 页面映射与后端注册表 ID 集合一致。

**GREEN：**

- 将稳定导航元数据和动态业务数据分离。
- 不在映射中放金额、状态、数量或业务列表。

**切片验收：**

```bash
cd ip_actor_wechat && npm run test:unit
cd ip_actor_wechat && node tests/blueprint.test.mjs
cd ip_actor_wechat && npm run build:weapp
```

建议提交：`feat(miniapp): consume unified screen data`

---

## 切片 5：统一模糊搜索选择

### 任务 5.1：提取搜索选择组件

**文件：**

- 新增 `ip_actor_wechat/src/components/SearchSelect/index.tsx`
- 新增 `ip_actor_wechat/src/components/SearchSelect/index.module.scss`
- 新增 `ip_actor_wechat/src/components/SearchSelect/index.test.tsx`
- 修改 `ip_actor_wechat/src/components/BlueprintScreen/index.tsx`

**RED：**

1. 输入 300ms 后才发请求，继续输入会取消前一次定时器。
2. 匹配结果按实体类型分组。
3. 点击列表项回传 `entityType/entityId/label/value`。
4. 无结果、失败和加载状态互斥。
5. 点击外部或完成选择后关闭下拉。

**GREEN：**

- 组件只管理搜索交互，不直接写项目草稿。
- 页面根据回调保存真实 ID 与显示值。

### 任务 5.2：接入真实搜索端点

**文件：**

- 修改 `app/miniapp_screens.py`
- 按缺口修改 `app/routes.py`
- 修改 `tests/test_miniapp_screens.py`
- 修改 `ip_actor_wechat/src/services/api.ts`
- 修改 `ip_actor_wechat/tests/blueprint.test.mjs`

**RED：**

1. 艺人、项目、场馆、城市、成员搜索均支持规范化关键词。
2. 返回项包含真实 `entity_id`。
3. 项目创建选择后持久化 `artist_id`/候选来源 ID；后续写操作不依赖名称反查。

**GREEN：**

- 优先复用 `/artists`、`/cases/search`、`/users`。
- 为场馆等缺失实体增加领域只读搜索接口，不在聚合接口内执行写入。

**切片验收：**

```bash
python3 -m pytest tests/test_miniapp_screens.py -q -k search
cd ip_actor_wechat && npm run test:unit -- SearchSelect
cd ip_actor_wechat && node tests/blueprint.test.mjs
```

建议提交：`feat(miniapp): unify entity search selectors`

---

## 切片 6：补齐领域模型与剩余页面（S01-S09、S19-S24、S61-S72、S82-S84）

### 任务 6.1：先写模型和幂等性测试

**文件：**

- 修改 `app/models.py`
- 修改 `app/schema.sql`
- 修改 `app/services.py`
- 新增 `tests/test_miniapp_domain_models.py`

**RED：**

逐表验证结构、租户归属和重复初始化：

- `venues`
- `tour_plans`
- `tour_stops`
- `notifications`
- `project_actuals`
- `ticketing_snapshots`
- `user_settings`
- `privacy_consents`
- `member_invitations`
- `agent_permissions`
- `project_drafts`

再次运行 `init_db()` 后，按业务唯一键计数不增加。

**GREEN：**

- 新增模型和 MySQL DDL。
- 将兼容性补列逻辑限制在现有表；新表由 `create_all`/DDL 管理。
- 只初始化有明确业务来源的基础选项，不初始化虚构财务、售票、通知或实际结果。

### 任务 6.2：发现与组合 provider（S04-S09、S19-S24）

**RED：**

- 演出、案例、机会、艺人、城市、档期和场馆均来自领域表。
- 无真实可比案例或机会时返回空状态。
- 场馆候选显示真实容量、报价及待核验字段。

**GREEN：**

- 实现发现、组合和搜索 provider。

### 任务 6.3：巡演与复盘 provider（S61-S66）

**RED：**

- 巡演路线按 `tour_stops.sequence` 排序。
- 售票进度取最新快照。
- 项目实际结果来自 `project_actuals`。
- 预测与实际差异由已保存值计算；无实际值时不显示差异。

**GREEN：**

- 实现巡演、售票、结算和复盘 provider。

### 任务 6.4：账户、协作与隐私 provider（S01-S03、S67-S72、S82-S84）

**RED：**

- 团队成员由 `TenantMember` 和 `User` 关联得到。
- 通知仅返回当前用户可见记录。
- 设置、通知偏好、隐私授权、邀请和 Agent 权限可读取已保存状态。
- S82 只返回服务连接元信息，不泄露密钥。

**GREEN：**

- 实现账户和设置 provider。
- 对应保存动作继续走独立领域写接口；缺失写接口按测试逐个补充。

**切片验收：**

```bash
python3 -m pytest tests/test_miniapp_domain_models.py tests/test_miniapp_screens.py -q
python3 -m pytest tests/test_main.py tests/test_miniapp_domain_models.py tests/test_miniapp_screens.py -q
```

建议提交：`feat(api): add remaining miniapp business domains`

---

## 切片 7：状态页、fixtures 清理与原生 runtime

### 任务 7.1：实现状态页 provider（S73-S81）

**文件：**

- 修改 `app/miniapp_screens.py`
- 修改 `tests/test_miniapp_screens.py`

**RED：**

- S73 仅在真实项目列表为空时成立。
- S74 要求有效已创建项目，不再回退 `/projects/1`。
- S75-S81 的恢复目标和上下文来自真实错误/版本状态。

**GREEN：**

- 状态页 provider 不返回通用示例 item。

### 任务 7.2：删除静态业务回退

**文件：**

- 删除 `ip_actor_wechat/src/data/fixtures.ts`
- 修改 `ip_actor_wechat/src/components/BlueprintScreen/index.tsx`
- 修改 `ip_actor_wechat/tools/generate-wechat-dist.mjs`
- 修改 `ip_actor_wechat/tests/blueprint.test.mjs`

**RED：**

增加静态防回退测试：

- 源码和生成脚本不得包含 `getFixtureItems`、`fixtureItems`、`loadState: 'example'`。
- 不得包含已知示例利润、示例项目和 `projectId || 1`/`taskId || 1`。
- 请求失败后 `items` 为空并保留重试入口。

**GREEN：**

- 删除 fixtures import、对象和 fallback。
- 原生 runtime 统一请求 `/miniapp/screens/{screen_id}`。
- 成功空结果使用 `empty_state`，失败使用 `error`。

### 任务 7.3：重新生成并验证 dist

**执行：**

```bash
cd ip_actor_wechat
node tools/generate-wechat-dist.mjs
node tests/blueprint.test.mjs
npm run build:weapp
```

**验收：**

- `dist/common/screens.js` 不含 fixtures。
- `dist/common/runtime.js` 不含逐页领域读取 `switch` 和示例回退。
- S01-S84 原生产物完整。

建议提交：`refactor(miniapp): remove fixture data fallbacks`

---

## 切片 8：全量契约、性能与回归验收

### 任务 8.1：84 页 API 映射矩阵

**文件：**

- 新增 `docs/miniapp-screen-api-matrix.md`
- 修改 `tests/test_miniapp_screens.py`
- 修改 `ip_actor_wechat/tests/blueprint.test.mjs`

矩阵逐页记录：

- screen ID
- provider key
- 必需上下文
- 读取实体
- 写接口
- 空状态
- 错误状态
- 已覆盖测试名

测试验证文档、后端注册表和前端映射三者 ID 集合完全一致。

### 任务 8.2：权限和查询次数

**RED：**

1. 对项目、任务、证据、版本、通知和巡演执行跨租户访问测试。
2. 对 S10、S34、S52、S61、S67 设置 SQL 查询次数上限。

**GREEN：**

- 修复遗漏的租户过滤。
- 使用批量查询、聚合查询或预加载消除 N+1。

### 任务 8.3：最终回归

```bash
python3 -m pytest tests/test_main.py tests/test_miniapp_screens.py tests/test_miniapp_domain_models.py -q
cd ip_actor_wechat && npm run test:unit
cd ip_actor_wechat && node tests/blueprint.test.mjs
cd ip_actor_wechat && npm run build:weapp
git diff --check
rg -n "fixtures|getFixtureItems|fixtureItems|loadState.*example|projectId.*\\|\\| 1|taskId.*\\|\\| 1" ip_actor_wechat/src ip_actor_wechat/tools ip_actor_wechat/dist
```

最后一条 `rg` 必须无匹配；若测试本身需要引用禁用词，只限制扫描生产目录。

### 任务 8.4：人工验收

- 微信开发者工具逐页打开 S01-S84。
- 验证加载、真实数据、空状态、错误重试和返回路径。
- 验证项目创建、财务测算、证据上传、门禁确认、决策、任务批处理、结算复盘和设置保存。
- 验证 320px、375px、430px 宽度无文字或控件重叠。
- 验证所有搜索选择框均可模糊查询、点击选择并保存真实 ID。

建议提交：`test: verify all miniapp screen data mappings`

---

## 附录：S01-S84 Provider 基线

| Screen | Provider key | Screen | Provider key |
| --- | --- | --- | --- |
| S01 | `auth_login` | S43 | `risk_list` |
| S02 | `tenant_select` | S44 | `risk_detail` |
| S03 | `privacy_scope` | S45 | `gate_list` |
| S04 | `discovery_public` | S46 | `gate_detail` |
| S05 | `discovery_dashboard` | S47 | `decision_confirm` |
| S06 | `case_list` | S48 | `decision_result` |
| S07 | `case_detail` | S49 | `version_compare` |
| S08 | `opportunity_detail` | S50 | `report_preview` |
| S09 | `discovery_search` | S51 | `report_share` |
| S10 | `project_list` | S52 | `agent_dashboard` |
| S11 | `project_detail` | S53 | `agent_plan` |
| S12 | `project_versions` | S54 | `agent_chat` |
| S13 | `project_create_basic` | S55 | `task_list` |
| S14 | `project_create_schedule` | S56 | `task_batch` |
| S15 | `project_create_scale` | S57 | `task_submit` |
| S16 | `project_create_costs` | S58 | `task_block` |
| S17 | `project_create_review` | S59 | `project_changes` |
| S18 | `project_draft` | S60 | `agent_permissions` |
| S19 | `artist_candidates` | S61 | `tour_overview` |
| S20 | `artist_detail` | S62 | `tour_route` |
| S21 | `artist_compare` | S63 | `tour_stop` |
| S22 | `city_compare` | S64 | `ticketing_progress` |
| S23 | `schedule_options` | S65 | `project_actuals` |
| S24 | `venue_options` | S66 | `project_review` |
| S25 | `finance_input` | S67 | `account_home` |
| S26 | `ticket_tiers` | S68 | `team_members` |
| S27 | `cost_breakdown` | S69 | `notifications` |
| S28 | `finance_conservative` | S70 | `user_settings` |
| S29 | `finance_neutral` | S71 | `data_permissions` |
| S30 | `finance_optimistic` | S72 | `member_invite` |
| S31 | `finance_breakeven` | S73 | `project_empty` |
| S32 | `finance_sensitivity` | S74 | `analysis_processing` |
| S33 | `finance_funding_gap` | S75 | `network_failure` |
| S34 | `judgement_summary` | S76 | `context_unavailable` |
| S35 | `judgement_explanation` | S77 | `permission_denied` |
| S36 | `assumption_list` | S78 | `version_changed` |
| S37 | `fact_list` | S79 | `validation_error` |
| S38 | `evidence_detail` | S80 | `archive_confirmation` |
| S39 | `evidence_conflicts` | S81 | `auth_expired` |
| S40 | `evidence_gaps` | S82 | `developer_connection` |
| S41 | `evidence_upload_context` | S83 | `notification_preferences` |
| S42 | `document_parse_review` | S84 | `privacy_records` |

---

## 完成定义

- S01-S84 后端 provider、前端映射和测试矩阵一一对应。
- 所有动态业务数据来自数据库或确定性后端计算。
- 没有 fixtures、示例业务回退、默认项目/任务 ID。
- 所有新增模型、provider、客户端方法和组件均有单元测试。
- 所有领域写接口兼容现有调用。
- 后端全量测试、前端单测、蓝图契约测试和微信构建通过。
