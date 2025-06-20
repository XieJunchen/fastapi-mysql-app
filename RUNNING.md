# FastAPI 镜像快速运行指南（RUNNING.md）

本说明面向直接拉取 Docker 镜像的用户，介绍如何启动 FastAPI 服务及数据库。

---

## 1. 拉取镜像

```bash
docker pull <your-dockerhub-username>/comfyui_workflow-fastapi-app:latest
```

---

## 2. 启动数据库（MySQL 示例）

```bash
docker run -d --name mysql \
  -e MYSQL_ROOT_PASSWORD=yourpassword \
  -e MYSQL_DATABASE=fastapi_db \
  -p 3306:3306 \
  mysql:8.0
```

---

## 3. 启动 FastAPI 服务

### 方式一：用环境变量
```bash
docker run -d --name fastapi-app \
  -e DATABASE_URL=mysql+pymysql://root:yourpassword@<mysql_host>:3306/fastapi_db \
  -p 8001:8001 \
  <your-dockerhub-username>/comfyui_workflow-fastapi-app:latest
```
- `<mysql_host>` 可为 `localhost`（本机测试）或 `mysql`（用 `--link mysql:mysql` 时）。

### 方式二：用 .env 文件
```bash
docker run -d --name fastapi-app \
  --env-file /path/to/.env \
  -p 8001:8001 \
  <your-dockerhub-username>/comfyui_workflow-fastapi-app:latest
```

---

## 4. 挂载配置文件/数据目录（如有）
```bash
docker run -d --name fastapi-app \
  --env-file /path/to/.env \
  -v /path/to/config.json:/app/config.json \
  -v /path/to/output:/app/output \
  -p 8001:8001 \
  <your-dockerhub-username>/comfyui_workflow-fastapi-app:latest
```

---

## 5. 常见问题
- Windows 路径需用绝对路径，建议加引号。
- 如有数据库等依赖服务，需确保网络互通或用 `--network` 参数。
- 端口如有冲突可自行调整。

---

## 6. 参考环境变量
- `DATABASE_URL`：数据库连接串，示例：`mysql+pymysql://root:yourpassword@mysql:3306/fastapi_db`
- 其他变量见 `.env.example` 或项目文档。

---

## 7. 官方推荐 docker-compose.yml 示例

你可以直接使用如下 `docker-compose.yml` 文件实现一键启动 FastAPI + MySQL 服务：

```yaml
version: '3.8'
services:
  fastapi-app:
    image: <your-dockerhub-username>/comfyui_workflow-fastapi-app:latest
    container_name: fastapi-app
    ports:
      - "8001:8001"
    volumes:
      - ./config.json:/app/config.json
      - ./output:/app/output
    env_file:
      - .env
    environment:
      - TZ=Asia/Shanghai
      - DATABASE_URL=mysql+pymysql://root:yourpassword@mysql:3306/fastapi_db
    depends_on:
      mysql:
        condition: service_healthy
    restart: always
  mysql:
    image: mysql:8.0
    container_name: mysql
    environment:
      - MYSQL_ROOT_PASSWORD=yourpassword
      - MYSQL_DATABASE=fastapi_db
      - TZ=Asia/Shanghai
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./all_data_mysql.sql:/docker-entrypoint-initdb.d/all_data_mysql.sql
    restart: always
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s
volumes:
  mysql_data:
```

> 请将 `<your-dockerhub-username>` 替换为你的 Docker Hub 用户名。

- 将此内容保存为 `docker-compose.yml`，与 `.env`、`config.json` 等文件放在同一目录。
- 然后执行：
  ```bash
  docker compose up -d
  ```
- 服务会自动启动并互联，无需手动拼装参数。

---

## 8. .env 文件示例

在 `docker-compose.yml` 同级目录下新建 `.env` 文件，内容如下（请根据实际情况修改）：
```env
# FastAPI MySQL/SQLite 环境变量示例
# MySQL 配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DB=fastapi_db

# FastAPI 主数据库连接串（MySQL 示例，用户名/密码/库名需与 compose 保持一致）
DATABASE_URL=mysql+pymysql://root:yourpassword@mysql:3306/fastapi_db

# Qiniu 配置
QINIU_ACCESS_KEY=your_access_key
QINIU_SECRET_KEY=your_secret_key
QINIU_BUCKET_NAME=your_bucket
QINIU_DOMAIN=your_domain

# ComfyUI 配置
COMFYUI_BASE_URL=http://localhost:8188
COMFYUI_VIDEO_URL=http://localhost:8188/video

# RunningHub 配置
RUNNINGHUB_API_URL=https://api.runninghub.com
RUNNINGHUB_API_KEY=your_api_key

# Douyin 配置
DOUYIN_APPID=your_appid
DOUYIN_APPSECRET=your_appsecret
DOUYIN_CLIENT_KEY=your_client_key
DOUYIN_CLIENT_SECRET=your_client_secret
DOUYIN_OPENAPI_TOKEN_URL=https://open.douyin.com/oauth/access_token/
DOUYIN_MINIAPP_TOKEN_URL=https://developer.toutiao.com/api/apps/token
DOUYIN_JSCODE2SESSION_URL=https://developer.toutiao.com/api/apps/jscode2session
```

```env
# 数据库连接串
DATABASE_URL=mysql+pymysql://root:yourpassword@mysql:3306/fastapi_db

# FastAPI 密钥等其他环境变量
SECRET_KEY=your_secret_key
TZ=Asia/Shanghai
# 其他自定义变量
```

- `.env` 文件不会被打包进镜像，也不会上传到仓库（已在 .gitignore/.dockerignore 中配置）。
- 启动 compose 时会自动加载，无需手动传参。

---

如需多服务一键部署或开发打包说明，请参考主项目 `README.md`。
