# 小程序数据库候选项实施计划

**目标：** 为项目创建 S13-S16 提供真实数据库高频候选、关键词模糊查询和点击回填，同时保持 Taro 与原生微信运行时行为一致。

**实现边界：**

- 仅用当前租户的 `Project`、`Venue`、`TourPlan/TourStop` 生成私有候选；艺人和演出为现有公开数据源。
- 保留手动输入，候选为空时不产生任何示例数据。
- 内部接口、数据库字段和实体 ID 不做重命名。
- 不把 `Venue.quote` 作为结构化的场馆成本候选。

## 任务 1：定义候选结构与后端测试

**文件：**
- 修改：`tests/test_miniapp_screens.py`
- 修改：`app/miniapp_screens.py`

**步骤：**

1. 为 S13-S16 新增失败测试，创建当前租户、其他租户、公开艺人/演出、场馆、巡演站点及多个历史项目。
2. 断言 `options.candidate_groups` 只包含当前租户的数据，且候选去重、过滤空/零值、每组最多 8 项。
3. 断言场馆候选带 `venue_id`、城市和容量的 `patch`，项目和艺人候选带真实实体 ID。
4. 在 `app/miniapp_screens.py` 新增候选构建辅助函数与稳定排序逻辑。
5. 扩展 `_project_create_screen` 返回 `candidate_groups`。
6. 运行指定 pytest 用例，确认由红转绿。

## 任务 2：补齐搜索与返回类型

**文件：**
- 修改：`app/routes.py`
- 修改：`app/schemas.py`（只在契约类型需要时）
- 修改：`tests/test_main.py` 或 `tests/test_miniapp_screens.py`

**步骤：**

1. 为城市/场馆/艺人/历史项目的模糊搜索补充或扩展测试，验证真实 ID、租户隔离和结果分组。
2. 扩展 `/miniapp/search` 的数据库查询和响应值，确保场馆选择可回填 ID、城市、容量。
3. 确保搜索不会使用静态回退数据。
4. 运行相关后端测试。

## 任务 3：实现 Taro 候选展示与点击回填

**文件：**
- 修改：`ip_actor_wechat/src/types/domain.ts`
- 修改：`ip_actor_wechat/src/components/SearchSelect/index.tsx`
- 修改：`ip_actor_wechat/src/components/SearchSelect/index.module.scss`
- 修改：`ip_actor_wechat/src/components/BlueprintScreen/index.tsx`
- 修改/新增：`ip_actor_wechat/src/components/SearchSelect/index.test.tsx`
- 修改：`ip_actor_wechat/src/components/BlueprintScreen/index.test.tsx`

**步骤：**

1. 先写失败测试：无输入时显示数据库高频候选，输入后显示模糊查询结果，点击后更新项目草稿。
2. 在领域类型中定义候选组、候选项和字段 patch。
3. 扩展 `SearchSelect` 支持初始候选、输入过滤、远程搜索结果与统一点选回调。
4. 在 S13-S16 使用 `candidate_groups` 渲染候选，不在组件中硬编码数据。
5. 场馆、艺人、项目候选通过 `patch` 原子更新草稿；数值候选写入对应数字字段。
6. 运行前端单元测试。

## 任务 4：实现原生微信 runtime

**文件：**
- 修改：`ip_actor_wechat/tools/generate-wechat-dist.mjs`
- 修改：`ip_actor_wechat/tests/blueprint.test.mjs`
- 生成：`ip_actor_wechat/dist/**`

**步骤：**

1. 先扩展 Node runtime 测试，验证 S14 首屏候选展示、关键词搜索和场馆选择后写入真实 `venue_id`。
2. 在生成器中加入候选项状态、初始渲染、关键词搜索分组和 `patch` 回填。
3. 重新生成 `dist`，禁止手工编辑生成文件。
4. 运行 `node tests/blueprint.test.mjs`。

## 任务 5：全量验证与视觉验收

**文件：**
- 修改：必要的测试或样式文件

**步骤：**

1. 运行后端全量 pytest、Taro 单元测试及原生运行时测试。
2. 通过 Skill 预览脚本启动预览，检查 S14 的移动端候选列表、搜索下拉、长文本和窄屏不溢出。
3. 执行 `git diff --check`，检查候选数据不含跨租户或静态模拟数据。
4. 提交实现。
