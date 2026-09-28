# 小程序统一业务详情页设计

## 目标

为 S01-S84 中所有具有真实持久化实体 ID 的列表项增加详情入口。用户点击列表项后进入统一详情页，读取数据库中的完整业务字段，并保持租户、项目和用户权限隔离。

不为以下派生展示项创建详情：城市聚合、成本项、财务指标、财务情景、证据缺口、证据冲突、项目档期、预测差异、版本字段变化、票档和临时报告摘要。这些条目没有独立持久化实体 ID。

## 支持实体

第一期统一覆盖：

- 公开实体：`show`、`artist`
- 项目实体：`project`、`project_version`、`fact`、`assumption`、`evidence`、`risk`、`gate`、`decision`、`task`
- 分析与报告：`document_parse_job`、`project_analysis_job`、`report_share`
- 组合与巡演：`venue`、`tour_plan`、`tour_stop`
- 复盘：`ticketing_snapshot`、`project_actual`
- 账户与协作：`tenant`、`tenant_member`、`notification`、`member_invitation`、`agent_permission`、`privacy_consent`

## 后端契约

新增：

`GET /miniapp/entities/{entity_type}/{entity_id}`

统一响应：

- `entity_type`、`entity_id`
- `title`、`subtitle`、`status`
- `media_url`：仅真实已保存媒体地址，没有则为 `null`
- `fields`：适合首屏扫描的键值字段
- `sections`：长文本、业务说明和结构化详情
- `related_items`：有真实关联 ID 的关联记录
- `actions`：只声明已存在的安全操作入口

列表聚合项新增可选 `detail_ref`：

```json
{
  "entity_type": "show",
  "entity_id": 3
}
```

后端在统一输出边界根据 `entity_type` 和 item `context` 自动补充 `detail_ref`，避免每个 provider 重复拼接。没有稳定实体 ID 的条目不返回该字段。

## 权限

- `show` 可匿名读取。
- `artist` 需要有效登录会话，沿用当前 S20 访问规则；详情不得包含内部凭据。
- 项目相关实体必须通过所属 `Project.tenant_id` 校验。
- `venue`、`tour_plan`、`tenant_member`、`member_invitation` 按当前租户校验。
- `tour_stop` 通过 `TourPlan.tenant_id` 校验。
- `notification`、`agent_permission`、`privacy_consent` 还必须属于当前用户。
- `report_share` 不返回分享 token。
- 实体不存在或实体不属于当前租户时返回 404，避免泄露实体是否存在；租户头指向非成员租户时返回 403，缺少认证返回 401。

## 前端交互

新增页面：

`pages/entity-detail/index`

列表项仅在存在 `detail_ref` 时可点击，并显示右侧详情箭头。点击后携带：

- `entityType`
- `entityId`

详情页不依赖列表缓存，始终调用详情接口重新读取真实数据。返回列表时使用小程序原生返回栈。

## 页面视觉

- 顶部使用实体标题、状态和简短副标题，不使用营销式大标题。
- 有真实媒体时使用全宽固定比例媒体区；无媒体时直接进入信息区，不显示占位图。
- 关键字段采用双列紧凑信息网格，小屏自动变为单列。
- 长文本使用无嵌套卡片的分组区块。
- 关联记录使用可点击行，并继续进入统一详情页。
- 底部只展示真实可执行操作；纯查看实体不显示空按钮。
- 加载、空数据、403、404 和网络错误分别展示明确状态与重试/返回入口。

## 原生 Runtime

生成脚本同步生成 `pages/entity-detail` 的 JS、JSON、WXML 和 WXSS。原生列表 runtime 读取 `detail_ref`，绑定统一点击事件并调用 `wx.navigateTo`。

Taro 构建和原生生成脚本均必须保留该页面，页面注册测试从 84 个蓝图页扩展为“84 个蓝图页 + 1 个统一详情页”。

## 测试

- 契约测试：`detail_ref` 仅出现在具有真实实体 ID 的 item。
- 后端测试：每个实体族至少覆盖一个成功详情；覆盖公开访问、跨租户 403/404、当前用户隔离和敏感字段不泄露。
- 前端测试：可详情项点击导航；不可详情项无点击行为；详情页成功、加载、404、403、网络重试。
- 原生测试：生成详情页文件、列表导航参数、详情接口请求与失败状态。
- 回归：后端全量、Vitest、Node 蓝图测试、微信构建和 `git diff --check`。
