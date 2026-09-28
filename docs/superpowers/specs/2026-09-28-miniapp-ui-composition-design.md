# 小程序公共 UI 与交互组合重构设计

## 目标

将 `BlueprintScreen` 中跨 84 个页面重复的展示、表单和列表交互拆分为可独立测试的 Taro 公共组件与 Hook；将原生微信生成器中的相应 WXML、WXSS 和运行时逻辑抽为模板片段和辅助函数。

现有页面路径、后端接口、存储键、屏幕状态机及用户可见交互保持不变。`BlueprintScreen` 仅负责按 `screenId` 编排业务表单、写操作和跳转目标。

## 范围与非目标

- 范围：Taro 端 84 个蓝图页与 `entity-detail`，以及 `tools/generate-wechat-dist.mjs` 生成的原生微信 `dist`。
- 范围：加载、空、错误状态；顶部栏与主视觉；字段网格；候选选择；项目复核；实体列表；任务批量选择。
- 非目标：重写后端聚合接口、变更实体详情接口、修改屏幕路由或将按屏写动作改为配置驱动。
- 非目标：让原生微信 `dist` 直接复用 Taro 组件。两端保留各自的渲染技术，但共享模板片段职责与测试覆盖。

## 组件边界

### 基础展示

- `ScreenHeader`：品牌栏、可选返回或主页入口、可选页面编码。主页跳转决策由调用方传入，不读取 session。
- `ScreenHero`：分组、标题、副标题、可选高亮与上下文标签。详情页可用同一组件但关闭蓝图上下文。
- `ScreenState`：加载、空态、错误态及调用方传入的重试/返回操作；不发起请求。
- `KeyValueGrid`：键值字段的紧凑网格。S17 项目复核和实体详情字段均通过数据项数组渲染。

### 表单

- `FormField`：文本或数字输入，受控值与 `onChange` 由页面提供。
- `CandidateField`：包装 `SearchSelect`，接收首屏候选、远程/本地搜索函数与点选回调；不理解 `ProjectDraft`。
- `ProjectReview`：使用 `KeyValueGrid`，只将项目草稿转换为六个复核字段。

### 列表和任务

- `BusinessList`：渲染 `DisplayItem`，有 `detailRef` 时调用 `onOpenDetail`；不做路由。
- `TaskBatchList`：维护或接收已选和展开任务 ID，输出选择、展开和详情回调；不调用批量任务接口，也不弹拒绝原因对话框。

## Hook 与数据边界

- `useMiniappScreenData`：接收 `screenId`、页面参数和上下文值，构造聚合接口上下文，处理加载、空、错误、权限跳转和下拉刷新，并输出标准化 `DisplayItem`。
- `useProjectDraft`：封装项目草稿默认值、读取、字段补丁、数值转换及 `Taro` 本地存储写入；候选 patch 仅允许白名单字段。
- 屏幕专属查询映射、登录、项目创建、财务计算、证据解析、工作派发等动作保留在 `BlueprintScreen`，避免把状态机和业务 API 迁入通用组件。

## 原生微信生成器

`tools/generate-wechat-dist.mjs` 拆分为纯模板片段和运行时辅助函数：

- 页面骨架：header、hero、state、business list、footer/actions。
- 交互片段：候选搜索和任务批量列表。
- 运行时：上下文构造、候选 patch、任务选择、详情导航与统一请求错误映射。

生成器仍输出每个页面完整的 WXML、WXSS、JS、JSON，`dist` 只由脚本生成，不手工编辑。模板片段使用现有页面状态字段，避免生成 API 或页面路由变化。

## 迁移顺序

1. 为基础展示组件、字段网格、表单、候选字段、业务列表和任务列表增加独立失败测试。
2. 实现组件与 Hook，使其通过独立测试。
3. 将 `entity-detail` 迁移到 `ScreenHeader`、`ScreenHero`、`ScreenState`、`KeyValueGrid` 和 `BusinessList`。
4. 将 `BlueprintScreen` 迁移到 Hook 与公共组件，保留现有业务动作函数和按屏表单选择。
5. 重构原生生成器模板与帮助函数，重新生成 `dist`。
6. 执行 Taro、原生 Node、后端回归与微信构建。

## 测试与验收

每个新增公共组件和 Hook 均有单元测试，至少覆盖：

- `ScreenHeader`：主页/返回入口显示与回调。
- `ScreenHero`：服务端摘要和可选状态/上下文。
- `ScreenState`：加载、空态操作、错误重试。
- `KeyValueGrid` 与 `ProjectReview`：字段渲染和待补回退。
- `FormField` 与 `CandidateField`：输入、首屏候选和选择回调。
- `BusinessList`：可详情项导航与无详情项不可点击。
- `TaskBatchList`：选择、取消选择、展开和详情回调。
- `useProjectDraft`：初始化、数值字段、候选 patch 白名单和持久化。
- `useMiniappScreenData`：所需上下文、空态、422 留页和 401/403/409 跳转。
- 原生生成器：模板片段应用到普通页、候选页、任务页和详情页，生成 runtime 保持候选回填、任务批量和详情导航行为。

验收要求：

- 所有既有 Taro 页面测试、原生 Node 测试、后端 pytest 均通过。
- `npm run build:weapp` 成功。
- `node tools/generate-wechat-dist.mjs` 后 `dist` 与测试预期一致。
- `git diff --check` 无空白错误。
- 不引入静态示例数据、`demo` 或 `MVP` 文案。
