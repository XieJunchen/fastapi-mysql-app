# FastAPI + MySQL/SQLite 容器化开发与打包指南

本项目基于 FastAPI 框架，支持 MySQL 和 SQLite，已实现 Docker 容器化一键部署，适合开发和生产环境。

## 目录结构

```
comfyUI_workflow/
├── app/                    # FastAPI 主应用目录
├── requirements.txt        # Python 依赖
├── Dockerfile              # 镜像构建文件
├── docker-compose.yml      # 容器编排，建议与 .env 同级
├── .env                    # 环境变量文件（本地/生产均建议放根目录）
├── .dockerignore           # Docker 构建忽略
├── .gitignore              # Git 忽略
├── config.json             # 主配置文件（可挂载覆盖）
├── all_data_sqlite.sql     # SQLite 初始化数据
├── all_data_mysql.sql      # MySQL 初始化数据
├── test.db                 # SQLite 数据库（开发环境自动生成）
├── output/                 # 输出目录（可选，建议挂载）
└── ...
```

## 本地开发与调试

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
2. 运行开发服务器：
   ```bash
   uvicorn app.main:app --reload --port 8001
   ```
3. 配置 `.env` 和 `config.json`，参考 `.env.example`。

## Docker 镜像打包与推送

1. 构建镜像：
   ```bash
   docker build -t comfyui_workflow-fastapi-app .
   ```
2. 本地测试镜像：
   ```bash
   docker run -d --name fastapi-app -p 8001:8001 comfyui_workflow-fastapi-app
   ```
3. 推送到 Docker Hub：
   ```bash
   docker tag comfyui_workflow-fastapi-app <your-dockerhub-username>/comfyui_workflow-fastapi-app:latest
   docker push <your-dockerhub-username>/comfyui_workflow-fastapi-app:latest
   ```

## 多服务一键部署（推荐生产/协同开发）

1. 配置 `.env` 和 `config.json`。
2. 启动所有服务：
   ```bash
   docker compose build
   docker compose up -d
   ```
3. 查看日志/停止服务：
   ```bash
   docker compose logs
   docker compose down
   ```

## 配置与环境变量说明
- `.env`：环境变量文件，已被 `.gitignore` 和 `.dockerignore` 忽略。
- `config.json`：主配置文件，支持挂载覆盖。

## 依赖说明
- FastAPI
- Uvicorn
- SQLAlchemy
- mysqlclient
- sqlite3（标准库）

## 贡献与维护
- 欢迎 issue 和 PR。
- 详细环境变量和敏感信息管理见 `.env` 文件。

---

> **外部用户如何直接运行镜像，请参考 RUNNING.md 文件。**