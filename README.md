# StarHub 演出平台

这是一个以“演出/艺人/AI 宣发”为核心的全栈应用，包含 Python FastAPI 后端和 React + Vite 前端。项目支持艺人热度查询、演出列表展示、AI 文案生成以及预约流程。

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
- 若未配置阿里云 DashScope API Key，则自动回退到本地兜底文案

### 4. 预约功能
- 用户可填写姓名和手机号预约演出
- 预约信息写入数据库

### 5. 项目决策闭环
- 支持 Web 登录并绑定默认客户空间
- 支持项目创建、项目版本留痕、三情景财务测算
- 支持人工推进决策与任务列表

### 6. 数据库
- 主库使用 MySQL 8.0，默认库名为 `ip_actor_platform`
- 默认连接配置写在 `app/config.py`，也可以通过 `DATABASE_URL` 环境变量覆盖
- 核心表包含 `tenants`、`users`、`projects`、`project_versions`、`decisions`、`tasks` 等

---

## 环境要求

- Python：3.11.x（已验证可用）
- Node.js：18.x / 20.x / 24.x（本项目已在 Node.js 24.15.0 + npm 11.12.1 环境下验证可用）
- npm：建议使用 10.x 及以上版本

## 技术栈

- 后端：FastAPI + SQLAlchemy + MySQL 8.0
- 前端：React + Vite + Axios
- 语言：Python / JavaScript
- AI 能力：可选接入 DashScope（Qwen）文本生成接口

---

## 快速启动（Windows / PowerShell）

### 1）创建并激活 Python 虚拟环境

```powershell
cd D:\code\IP_actor_platform
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2）启动后端

```powershell
cd D:\code\IP_actor_platform
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL="mysql+pymysql://root:123456789@127.0.0.1:3306/ip_actor_platform?charset=utf8mb4"
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

如果使用 `app/config.py` 中的默认连接配置，可以省略 `$env:DATABASE_URL=...`。

后端地址：

```text
http://localhost:8000
```

### 3）安装并启动前端

```powershell
cd D:\code\IP_actor_platform\starhub-web
npm install
npm run dev
```

前端地址：

```text
http://localhost:5173
```

> 若你已经使用过项目并创建了 `.venv`，直接执行 `./.venv/Scripts/Activate.ps1` 即可，无需重复创建。

---

## 项目结构

```text
IP_platform/
├─ main.py                 # 兼容入口，保留 uvicorn main:app 启动方式
├─ app/                    # FastAPI 后端应用包
│  ├─ main.py              # 应用工厂与路由注册
│  ├─ database.py          # 数据库连接与会话依赖
│  ├─ models.py            # SQLAlchemy ORM 模型
│  ├─ schemas.py           # Pydantic 入参与出参模型
│  ├─ routes.py            # API 路由层
│  ├─ services.py          # 业务逻辑、种子数据与财务计算
│  └─ responses.py         # 统一响应结构
├─ requirements.txt        # Python 依赖
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

### 5. Phase 1 项目决策接口
- `POST /auth/web-login`
  - Web 端登录，返回统一 token 与当前客户空间
- `GET /tenants`
  - 获取可用客户空间
- `POST /tenants/switch`
  - 切换客户空间
- `GET /projects`
  - 获取当前客户空间项目列表
- `POST /projects`
  - 创建项目并生成初始版本
- `GET /projects/{project_id}`
  - 获取项目详情与当前版本
- `GET /projects/{project_id}/versions`
  - 获取项目版本列表
- `POST /finance/calculate`
  - 执行三情景财务测算，并生成新的版本快照
- `POST /decisions`
  - 提交人工决策
- `GET /tasks`
  - 获取任务列表，可按 `project_id` 过滤
- `POST /tasks`
  - 创建任务

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
export DATABASE_URL='mysql+pymysql://root:123456789@127.0.0.1:3306/ip_actor_platform?charset=utf8mb4'
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

如果使用 `app/config.py` 中的默认连接配置，可以省略 `export DATABASE_URL=...`。

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

AI 文案生成优先调用本地 `llama_server`，然后再尝试 DashScope，最后使用本地兜底文案。

### 1）本地 llama_server

默认配置写在 `app/config.py`：

```python
LLAMA_SERVER_URL = 'http://127.0.0.1:8080/v1/chat/completions'
LLAMA_SERVER_MODEL = 'local-model'
```

如果你的本地服务端口或模型名不同，可以用环境变量覆盖：

```bash
export LLAMA_SERVER_URL='http://127.0.0.1:8080/v1/chat/completions'
export LLAMA_SERVER_MODEL='qwen-local'
```

接口按 llama.cpp server 的 OpenAI-compatible `/v1/chat/completions` 格式调用。

如果暂时不想调用本地大模型，可以显式关闭：

```bash
export LLAMA_SERVER_URL=''
```

### 2）DashScope 兜底

如果本地 `llama_server` 不可用，且配置了 DashScope Key，会继续调用 DashScope：

```bash
export DASHSCOPE_API_KEY=your_key
```

或者：

```bash
export DASHSCOPE_API_TOKEN=your_token
```

如果两类大模型都不可用，则会自动使用本地兜底文案，保证前端可正常使用。

---

## 业务场景

该项目适合以下场景：
- 演出平台的前端工作台
- 艺人数据展示与热度分析
- 一站式 AI 宣发内容生成
- 预约和报名测试流程

---

## 注意事项

1. 前端默认请求地址为 `http://localhost:8000`，如果后端运行在其他机器或端口，请修改 `starhub-web/src/api.js` 中的 `baseURL`。
2. MySQL 首次启动时会自动创建业务表和默认客户空间；后端不再创建或依赖本地 SQLite 数据库文件。
3. 生产部署前需补充权限、审计、监控与数据治理能力。

---

## 贡献与扩展建议

可以继续扩展：
- 增加用户登录与权限管理
- 引入真实演出票务系统
- 接入真实的艺人库与演出库
- 提升 AI 文案质量，支持更多宣传场景
- 增加订单详情、支付、退款等流程
