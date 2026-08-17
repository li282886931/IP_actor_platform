# StarHub 演出平台 Demo

这是一个以“演出/艺人/AI 宣发”为核心的全栈 Demo，包含 Python FastAPI 后端和 React + Vite 前端。项目用于演示艺人热度查询、演出列表展示、AI 文案生成以及预约流程。

## 功能概览

### 1. 艺人查询
- 支持按艺人名称搜索
- 返回艺人热度、粉丝量、风险等级、标签等信息
- 可根据艺人热度给出城市推荐建议

### 2. 演出展示
- 展示演出列表（按城市筛选）
- 查看单个演出详情
- 展示演出时间、场馆、票价、状态等信息

### 3. AI 宣发内容生成
- 支持生成海报文案或短视频脚本
- 输入演出名称、艺人、城市等信息后，可生成宣传语
- 若未配置阿里云 DashScope API Key，则自动回退到 mock 文案

### 4. 预约功能
- 用户可填写姓名和手机号预约演出
- 预约信息写入数据库

### 5. 数据库与示例数据
- 使用 SQLite 数据库
- 启动时自动创建 `demo.db` 并写入初始化数据
- 包含 `artists`、`shows`、`orders`、`ai_generations` 等表

---

## 技术栈

- 后端：FastAPI + SQLAlchemy + SQLite
- 前端：React + Vite + Axios
- 语言：Python / JavaScript
- AI 能力：可选接入 DashScope（Qwen）文本生成接口

---

## 项目结构

```text
IP_platform/
├─ main.py                 # FastAPI 后端入口
├─ requirements.txt        # Python 依赖
├─ demo.db                # SQLite 数据库（首次启动自动生成）
├─ starhub-web/           # React 前端工程
│  ├─ src/
│  ├─ package.json
│  ├─ vite.config.js
│  └─ README.md
└─ README.md              # 项目说明文档
```

---

## 后端 API 说明

### 1. 艺人接口
- `GET /artists?q=周杰伦`
  - 查询艺人列表，可按名称模糊搜索
- `GET /artists/{artist_id}`
  - 获取艺人详情及城市推荐建议

### 2. 演出接口
- `GET /shows`
  - 获取演出列表，可按 `city` 参数过滤
- `GET /shows/{show_id}`
  - 获取单个演出详情
- `POST /shows/{show_id}/order`
  - 提交预约信息，参数：`name`, `phone`

### 3. AI 生成接口
- `POST /ai/generate`
  - 参数示例：

```json
{
  "type": "poster",
  "show_name": "周杰伦演唱会",
  "artist": "周杰伦",
  "city": "北京"
}
```

返回结构示例：

```json
{
  "code": 0,
  "data": {
    "result": "🎵 周杰伦演唱会 ..."
  },
  "message": "ok"
}
```

### 4. 健康检查
- `GET /ping`
  - 返回 `{"ok": true}`

---

## 使用方法

### 方式一：本地开发环境启动

#### 1）安装后端依赖

```bash
cd IP_platform
pip install -r requirements.txt
```

#### 2）启动 FastAPI 后端

```bash
cd IP_platform
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

后端默认地址：

```text
http://localhost:8000
```

#### 3）安装并启动前端

```bash
cd IP_platform/starhub-web
npm install
npm run dev
```

前端默认地址：

```text
http://localhost:5173
```

#### 4）访问页面
- 打开浏览器访问前端地址
- 进入页面后可浏览演出、查询艺人、生成 AI 文案并预约演出

---

### 方式二：直接运行后端（适合调试接口）

如果只需要接口调试，可以直接运行：

```bash
cd IP_platform
python main.py
```

注意：本项目是 FastAPI 应用，推荐使用 `uvicorn` 方式启动，启动效果更稳定。

---

## AI 功能说明

AI 文案生成功能会读取环境变量：

```bash
export DASHSCOPE_API_KEY=your_key
```

或者：

```bash
export DASHSCOPE_API_TOKEN=your_token
```

如果未配置，则会自动使用本地 mock 文案，保证前端可正常演示。

---

## 业务场景

该项目适合以下场景：
- 演出平台的前端 Demo
- 艺人数据展示与热度分析
- 一站式 AI 宣发内容生成
- 预约和报名测试流程

---

## 注意事项

1. 前端默认请求地址为 `http://localhost:8000`，如果后端运行在其他机器或端口，请修改 `starhub-web/src/api.js` 中的 `baseURL`。
2. 数据库首次启动时会自动初始化示例数据，若需要重置数据库，可删除 `demo.db` 后重新启动。
3. 本项目为 Demo，适合演示与二次开发，不建议直接作为生产环境系统使用。

---

## 贡献与扩展建议

可以继续扩展：
- 增加用户登录与权限管理
- 引入真实演出票务系统
- 接入真实的艺人库与演出库
- 提升 AI 文案质量，支持更多宣传场景
- 增加订单详情、支付、退款等流程

如果你需要，我也可以继续为这个项目补一份更详细的“接口文档版 README”或者生成中文/英文双语说明。