# Docker Compose 部署

本套文件部署网页、FastAPI、MySQL、Redis 和 MinIO。网页通过同域 `/api` 请求后端，Nginx 对 AI SSE 关闭缓冲，并使用 450 秒代理超时。小程序源码不参与网页镜像构建。

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

若宿主机已有模型服务占用 `8080`，或已有 MinIO 占用 `9000/9001`，先在 `deployment.env` 修改 `WEB_PORT`、`MINIO_PORT`、`MINIO_CONSOLE_PORT` 为空闲端口；容器之间仍使用各自内部端口。

root 页面仅创建角色账号。首次启动将仍使用原默认密码的 root 改为该初始密码；仍使用原默认密码的六类预置角色账号会停用并随机化密码，随后由 root 创建正式账号。已有非默认密码、角色账号状态和 root 密码保留；修改 `INITIAL_ROOT_PASSWORD` 不会覆盖已有 root 密码。

## 文件与服务

| 文件 | 作用 |
|---|---|
| `docker-compose.yml` | 五个服务、健康依赖、持久卷、日志轮转 |
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
| minio | 仅本机 `9000`、`9001` | `minio_data` |

Compose 项目名默认为 `ip-actor-platform`，持久卷名带项目名前缀。可通过 `-p` 部署另一套隔离环境，同时修改网页和 MinIO 端口。不要将旧版 MySQL 数据目录直接挂载到新版本容器。

MySQL 默认 8.0，与项目现有数据库版本保持一致，使用 utf8mb4；升级数据库大版本需要另行验证。MinIO 使用已确认版本为 `RELEASE.2025-09-07T16-13-09Z` 的镜像摘要，可通过 `MINIO_IMAGE` 替换为已批准的镜像仓库地址；默认不使用浮动 latest。镜像拉取受 Docker Hub／Quay 网络和访问权限影响，有镜像代理时可设置 `PYTHON_IMAGE`、`NODE_IMAGE`、`NGINX_IMAGE`、`MYSQL_IMAGE`、`REDIS_IMAGE`、`MINIO_IMAGE`，无需修改 Dockerfile。

## AI、网页读取与微信

编辑 `deployment.env`：

```dotenv
LLAMA_SERVER_URL=http://host.docker.internal:8080/v1/chat/completions
LLAMA_SERVER_MODEL=qwen-local
ANALYSIS_ALLOWED_ORIGINS=https://实际MCP服务,https://实际API服务
WECHAT_MINIAPP_APPID=实际小程序AppID
WECHAT_MINIAPP_SECRET=实际小程序Secret
```

`host.docker.internal` 指向宿主机；容器中的 `127.0.0.1` 只指向该容器。宿主机模型服务必须监听容器能到达的地址，例如 `0.0.0.0:8080`；不必公开模型端口到公网。其他服务器上的模型使用真实服务地址。

默认 `LLAMA_SERVER_URL` 为空，防止误访问容器自身的 8080 端口。未配置模型时沿用当前应用的明确回退行为；此套文件不附带 GPU、模型权重或模型服务。模型输出上限 800 token，应用既有 AI 超时为 300 秒，Nginx 超时覆盖读取与综合研判。

需要外部凭据时复制 `deployment.connectors.env.example` 为 `deployment.connectors.env`，填写当前数据源实际使用的 `DATA_CONNECTOR_SECRET_<REF>` 或已有云模型密钥，并设权限 `0600`。该文件仅注入后端，默认不存在也可启动。修改环境配置后执行：

```bash
docker compose --env-file deployment.env up -d
```

实时来源还需在业务库配置 `DataSource` 的空间、项目、角色、只读工具和 endpoint，并配置项目职责授权。环境变量不会自动创建来源记录或代表第三方已接通。

## 报告和 MinIO 的当前边界

默认沿用应用已有报告下载路径，报告文件写入持久卷。内部配置值 `OSS_PROVIDER` 保持现有本地模式，以保证生成报告后经 `/api/reports/files/...` 下载可用。

MinIO 已部署并提供内部 S3 地址 `minio:9000`，控制台默认只允许服务器本机访问。远程管理可使用 SSH 转发，例如：

```bash
ssh -p 31484 -L 9001:127.0.0.1:9001 root@服务器地址
```

之后打开本机 `http://127.0.0.1:9001`，账号取 `MINIO_ROOT_USER`、密码取 `MINIO_ROOT_PASSWORD`。

当前应用切换到 `OSS_PROVIDER=minio` 后会生成内部 MinIO 地址的上传签名，报告返回 `minio://` URI；浏览器公网直传和报告下载尚未完整接线。因此默认未切换对象存储，不应只改开关就当作完整的浏览器 MinIO 支持。上线对象存储需要补充可访问的签名地址、HTTPS／跨域和报告下载实现。

## 维护与数据迁移

```bash
docker compose --env-file deployment.env logs --tail=100 backend web
docker compose --env-file deployment.env up -d --build
docker compose --env-file deployment.env down
```

`down` 只停止和删除容器／网络，保留持久卷。不要对需要保留数据的环境执行 `down -v`。数据库和 MinIO 初始凭据只在空卷初始化时生效；已有卷改环境变量不会自动修改服务内密码，需先完成数据库／存储用户密码变更。

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

恢复期间停止业务流量，完成数据库与文件一致性检查后重启后端。若导入后覆盖了 root 或默认角色账号，后端启动会再次处理仍使用原默认密码的账号。已有独立数据库迁移使用逻辑导出／导入，不直接复制不同版本的数据卷。MinIO 对象另行通过 S3 备份工具或一致性存储快照备份；Redis 不作为业务数据唯一来源。

## HTTPS

默认提供 HTTP，可放在现有 HTTPS 网关之后。外层网关同样应关闭 `/api` SSE 缓冲并设置至少 450 秒超时。`WEB_BIND_IP=127.0.0.1` 可限制为本机网关访问；若需要直接从外部访问，使用对应网卡地址并配置防火墙。此套文件不自动申请域名证书或修改服务器防火墙。

验证状态见同目录 [部署验收记录](verification.md)。
