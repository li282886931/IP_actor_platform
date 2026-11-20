# Docker Compose 部署

本套文件部署网页、FastAPI、MySQL 和 Redis。网页通过同域 `/api` 请求后端，Nginx 对 AI SSE 关闭缓冲，并使用 450 秒代理超时。小程序源码不参与网页镜像构建。

## 启动

需要 Docker Engine 24+、Docker Compose 2.24+ 和 Python 3。macOS 可使用 Docker Desktop；Linux 建议使用仍在维护的 Ubuntu、Debian 或 Rocky Linux。现有 CentOS 7 已停止维护，不作为已验证的部署系统。

在项目根目录执行：

```bash
python3 deploy/bootstrap.py --generate-env
docker compose --env-file deployment.env up -d --build
```

第一条命令生成权限为 `0600` 的 `deployment.env`，六个秘密值独立随机生成，已有文件不会覆盖。不要提交该文件。数据库连接 URL 由启动脚本构造并转义密码，数据库账号为独立的 `ip_actor` 用户。

默认网页地址为 `http://服务器地址:8080`；本机为 `http://127.0.0.1:8080`。root 初始密码读取本地 `deployment.env` 的 `INITIAL_ROOT_PASSWORD`：

```bash
rg '^INITIAL_ROOT_PASSWORD=' deployment.env
docker compose --env-file deployment.env ps
```

若宿主机已有模型服务占用 `8080`，先在 `deployment.env` 修改 `WEB_PORT` 为空闲端口；容器之间仍使用各自内部端口。

root 页面仅创建角色账号。首次启动将仍使用原默认密码的 root 改为该初始密码；仍使用原默认密码的六类预置角色账号会停用并随机化密码，随后由 root 创建正式账号。已有非默认密码、角色账号状态和 root 密码保留；修改 `INITIAL_ROOT_PASSWORD` 不会覆盖已有 root 密码。

## 文件与服务

| 文件 | 作用 |
|---|---|
| `docker-compose.yml` | 四个服务、健康依赖、持久卷、日志轮转 |
| `Dockerfile.backend` | Python 3.11，非 root 进程、单 worker |
| `Dockerfile.web` | Node 22 构建、Nginx 1.28 服务 |
| `deploy/nginx.conf` | `/api` 代理、SPA 路由和 SSE |
| `deploy/bootstrap.py` | 生成秘密配置、构造连接 URL、初始化账号 |
| `deployment.env.example` | 非敏感配置模板 |
| `deployment.connectors.env.example` | 外部连接器凭据模板 |
| `.dockerignore` | 排除本地密钥、缓存、文档、依赖和构建产物 |

| 服务 | 默认宿主机端口 | 持久卷 |
|---|---|---|
| web | `8080` | 镜像内静态文件 |
| backend | 不发布 | `reports_data` → `/app/storage` |
| mysql | 不发布 | `mysql_data` |
| redis | 不发布 | `redis_data`，开启 AOF、启用密码 |

Compose 项目名默认为 `ip-actor-platform`，持久卷名带项目名前缀。可通过 `-p` 部署另一套隔离环境，同时修改网页端口。不要将旧版 MySQL 数据目录直接挂载到新版本容器。

MySQL 默认 8.0，与项目现有数据库版本保持一致，使用 utf8mb4；升级数据库大版本需要另行验证。镜像拉取受 Docker Hub 网络和访问权限影响，有镜像代理时可设置 `PYTHON_IMAGE`、`NODE_IMAGE`、`NGINX_IMAGE`、`MYSQL_IMAGE`、`REDIS_IMAGE`，无需修改 Dockerfile。

## AI、网页读取与微信

编辑 `deployment.env`：

```dotenv
LLM_PROVIDER=siliconflow
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_MODEL=Qwen/Qwen3.5-35B-A3B
SILICONFLOW_MAX_TOKENS=8192
SILICONFLOW_THINKING_BUDGET=2048
SILICONFLOW_API_KEY=实际硅基流动API密钥
LLAMA_SERVER_TIMEOUT_SECONDS=300
LLAMA_SERVER_MAX_TOKENS=800
ANALYSIS_ALLOWED_ORIGINS=https://实际MCP服务,https://实际API服务
WECHAT_MINIAPP_APPID=实际小程序AppID
WECHAT_MINIAPP_SECRET=实际小程序Secret
```

Docker 默认使用硅基流动；模型名称须与账号可用模型列表一致，示例模型并不代表已验证账号权限。`SILICONFLOW_BASE_URL` 支持以 `/v1` 结尾的基础地址或完整 `/v1/chat/completions` 地址，要求 HTTPS。硅基流动密钥填写在 `deployment.env` 或运行 Compose 的环境变量中，仅注入后端，不放入 Web 构建参数或仓库。

同步与流式调用均使用 Bearer 认证、顶层 `enable_thinking=true`、300秒超时。硅基流动采用服务端默认采样，不继承本地模型的 temperature、top_p 和 frequency_penalty。硅基流动以 `SILICONFLOW_MAX_TOKENS` 设置输出上限，默认8192 token，供思考及完整宣发方案共同使用；`SILICONFLOW_THINKING_BUDGET` 默认2048，限制内部思考占用，仍保持思考开启。本地模式仍以 `LLAMA_SERVER_MAX_TOKENS` 设置，默认800。允许模型内部思考，提示词不再使用 `/no_think`。正式结果清洗推理标签，内部推理不向前端发送。配置不完整返回503；云端调用失败返回502或SSE `error`，不保存兜底文案，不自动切换其他付费服务。切换云模型、思考模式或输出预算会隔离生成缓存。

云端正文须使用正式方案的 Markdown 标题；标题前的分析不展示、不保存，没有正式标题则返回生成失败。提示词要求缺失信息标注“待确认”，未核验的演出权益、声学技术和票务状态不得写成事实。输出约束版本也参与缓存隔离。提示词与过滤不能替代人工核验，实际发布前仍须核验方案中的事实及素材授权。

直接启动 Python 也默认使用硅基流动；需要本地模型时显式配置：

```dotenv
LLM_PROVIDER=llama-server
LLAMA_SERVER_URL=http://host.docker.internal:8080/v1/chat/completions
LLAMA_SERVER_MODEL=qwen-local
LLAMA_SERVER_TIMEOUT_SECONDS=300
LLAMA_SERVER_MAX_TOKENS=800
ANALYSIS_ALLOWED_ORIGINS=https://实际MCP服务,https://实际API服务
WECHAT_MINIAPP_APPID=实际小程序AppID
WECHAT_MINIAPP_SECRET=实际小程序Secret
```

`host.docker.internal` 指向宿主机；容器中的 `127.0.0.1` 只指向该容器。宿主机模型服务必须监听容器能到达的地址，例如 `0.0.0.0:8080`；不必公开模型端口到公网。其他服务器上的模型使用真实服务地址。

本地模式下 Docker 的 `LLAMA_SERVER_URL` 默认为空，防止误访问容器自身的8080端口，仅本地模式保留已有回退行为。此套文件不附带 GPU、模型权重或模型服务。Nginx 超时覆盖读取与综合研判。

需要外部凭据时复制 `deployment.connectors.env.example` 为 `deployment.connectors.env`，填写当前数据源实际使用的 `DATA_CONNECTOR_SECRET_<REF>` 或已有云模型密钥，并设权限 `0600`，同时在 `deployment.env` 设置 `CONNECTOR_ENV_FILE=./deployment.connectors.env`。默认空示例文件仅注入后端且可直接启动。修改环境配置后执行：

```bash
docker compose --env-file deployment.env up -d --build backend
```

真实密钥不得写入数据库、前端配置或接口请求。`DataSource.credential_ref`
只保存环境变量引用名，例如 `AMAP_PROD` 对应
`DATA_CONNECTOR_SECRET_AMAP_PROD`；接口只返回引用名与
`configured`/`missing` 状态，不回显密钥。配置后必须重新创建 backend
容器，再在当前空间注册连接器、执行连接测试并由管理员启用。

实时来源还需配置空间、项目、角色、只读工具和 endpoint，并配置项目职责授权。环境变量不会自动创建来源记录或代表第三方已接通。`contract_required`、`adapter_required` 和 `runner_required` 目录项不会因为填写任意密钥而变为可测试或可启用。

## 报告和阿里 OSS 的当前边界

默认沿用应用已有报告下载路径，报告文件写入持久卷。内部配置值 `OSS_PROVIDER` 保持现有本地模式，以保证生成报告后经 `/api/reports/files/...` 下载可用。

如需接入阿里 OSS，设置 `OSS_PROVIDER=aliyun-oss`，并填写 `ALIYUN_OSS_ENDPOINT`、`ALIYUN_OSS_BUCKET`、`ALIYUN_OSS_ACCESS_KEY_ID`、`ALIYUN_OSS_ACCESS_KEY_SECRET`。浏览器直传会使用后端生成的 PUT 签名 URL；后端生成的可行性报告会直接写入 OSS。若配置 `ALIYUN_OSS_PUBLIC_BASE_URL`，报告下载地址使用该公开域名，否则返回 `oss://bucket/key` 供后端或内部系统处理。

已有 ossutil 凭据时，可使用 `deploy/configure_aliyun_oss.py --env deployment.env --oss-config /实际路径/.ossutilconfig --bucket 实际桶名` 配置。工具兼容 `[Credentials]` 与 ossutil v2 `[default]`，将凭据注入后端环境变量，强制 HTTPS Endpoint，备份后原子更新部署文件；原文件及备份权限为 0600，日志不输出密钥。宿主机 `/root/.ossutilconfig` 不会自动出现在非 root 后端容器中；直接注入环境变量后无需把 root 的配置文件挂载给应用。

宣发图片另需固定文生图服务的 `IMAGE_GENERATION_AUTHORIZATION`，值为该服务接受的完整 Authorization 请求头。硅基流动文本模型密钥不适用于此服务。只填入后端部署配置，修改后重新创建后端容器；未取得服务方有效授权前，文生图接口仍不可用。图片展示使用 HTTPS CDN 或 3600 秒私有桶签名地址，数据库保留对象信息，链接过期时重新获取。

缺失或格式无效的授权返回 503，且不发起出图请求；上游拒绝授权返回 502，网络或 TLS 失败返回对应的 502 提示，连接/生成超时返回 504。不要把配置缺失当作暂时失败反复重试。服务器还必须能够访问此服务：2026-11-16 实测域名解析到 `10.8.x.x` 与 `fdbd:...` 内网地址，当前部署服务器无法连接。应由服务方提供授权的访问路由或代理；只填写密钥无法解决网络不可达。不得使用文本模型密钥、OSS AK/SK 或开发工具会话替代文生图授权。

如需接入外部 MinIO 或 S3 兼容服务，设置 `OSS_PROVIDER=minio`，并填写 `MINIO_ENDPOINT`、`MINIO_BUCKET`、`MINIO_SECURE`、`MINIO_ACCESS_KEY`、`MINIO_SECRET_KEY`。当前 Compose 不内置对象存储服务，需要使用已有对象存储地址或单独部署。

## 维护与数据迁移

```bash
docker compose --env-file deployment.env logs --tail=100 backend web
docker compose --env-file deployment.env up -d --build
docker compose --env-file deployment.env down
```

`down` 只停止和删除容器／网络，保留持久卷。不要对需要保留数据的环境执行 `down -v`。数据库初始凭据只在空卷初始化时生效；已有卷改环境变量不会自动修改服务内密码，需先完成数据库用户密码变更。

应用当前启动会创建缺失表、补充既有列并更新既有参考资料；不是独立版本化迁移系统。单 worker 避免多个进程并发执行初始化。恢复或升级现有业务库前先备份，并核对当前初始化逻辑对参考资料的更新行为。当前旧版业务接口尚未完成统一权限治理，生产公网访问前需完成权限收敛；本套容器配置不代表应用已通过安全验收。

备份数据库与本地报告：

```bash
set -o pipefail
umask 077
mkdir -p backups
docker compose --env-file deployment.env exec -T mysql sh -c \
  'MYSQL_PWD="$MYSQL_PASSWORD" mysqldump --user="$MYSQL_USER" --single-transaction --no-tablespaces --routines --events --triggers "$MYSQL_DATABASE"' \
  | gzip > backups/database.sql.gz
docker compose --env-file deployment.env exec -T backend \
  tar -C /app/storage -czf - . > backups/reports.tar.gz
```

恢复到目标环境的空数据库和报告卷：

```bash
gzip -dc backups/database.sql.gz | docker compose --env-file deployment.env exec -T mysql sh -c \
  'MYSQL_PWD="$MYSQL_PASSWORD" mysql --user="$MYSQL_USER" "$MYSQL_DATABASE"'
docker compose --env-file deployment.env exec -T backend \
  tar -C /app/storage -xzf - < backups/reports.tar.gz
```

恢复期间停止业务流量，完成数据库与文件一致性检查后重启后端。若导入后覆盖了 root 或默认角色账号，后端启动会再次处理仍使用原默认密码的账号。已有独立数据库迁移使用逻辑导出／导入，不直接复制不同版本的数据卷。若启用阿里 OSS，对象文件应通过 OSS 工具或存储侧快照备份；Redis 不作为业务数据唯一来源。

## HTTPS

默认提供 HTTP，可放在现有 HTTPS 网关之后。外层网关同样应关闭 `/api` SSE 缓冲并设置至少 450 秒超时。`WEB_BIND_IP=127.0.0.1` 可限制为本机网关访问；若需要直接从外部访问，使用对应网卡地址并配置防火墙。此套文件不自动申请域名证书或修改服务器防火墙。

验证状态见同目录 [部署验收记录](verification.md)。
