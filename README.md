# FastAPI + MySQL/SQLite 容器化部署项目

本项目基于 FastAPI 框架，支持 MySQL 和 SQLite，已实现 Docker 容器化一键部署，支持自动数据库初始化，适合开发和生产环境。

## 目录结构

```
fastapi-mysql-app/
├── app/                # FastAPI 主应用目录
├── requirements.txt    # Python 依赖
├── Dockerfile          # 镜像构建文件
├── docker-compose.yml  # 容器编排
├── .dockerignore       # Docker 构建忽略
├── README.md           # 项目说明
├── all_data_sqlite.sql # SQLite 初始化数据（自动导入）
├── all_data_mysql.sql  # MySQL 初始化数据（可选）
├── test.db             # SQLite 数据库（开发环境自动生成）
└── ...
```

## 快速开始

### 1. 克隆项目
```bash
git clone <your-repo-url>
cd fastapi-mysql-app
```

### 2. 配置数据库
- 默认支持 MySQL 和 SQLite，相关配置在 `.env` 和 `config.json` 中管理。
- **开发环境**：如无数据库文件，启动时会自动用 `all_data_sqlite.sql` 初始化 SQLite。
- **生产环境**：建议使用 MySQL，首次启动可用 `all_data_mysql.sql` 初始化。

### 3. 启动方式

#### 方式一：推荐，使用 Docker Compose（适合多服务协同/生产环境）
```bash
docker compose build
docker compose up -d
```
- 一键启动 FastAPI + MySQL 等多服务，适合生产或需要数据库协同的场景。

#### 方式二：仅主服务，直接用 Docker 启动（适合开发/测试/单服务）
```bash
docker build -t fastapi-mysql-app .
docker run -d -p 8000:8000 --env-file .env \
  -v $(pwd)/config.json:/app/config.json \
  -v $(pwd)/output:/app/output \
  fastapi-mysql-app
```
- 只运行 FastAPI 主服务，适合本地开发、测试或不依赖数据库容器的场景。
- Windows 路径请将 `$(pwd)` 替换为绝对路径。

### 4. 配置文件说明
- `.env`：环境变量文件，参考 `.env.example` 复制并修改。
- `config.json`：主配置文件，支持挂载覆盖。

### 5. 数据库初始化说明
- **SQLite**：首次启动自动检测 `test.db`，如不存在则自动用 `all_data_sqlite.sql` 初始化。
- **MySQL**：可用 `all_data_mysql.sql` 手动初始化，或用 Docker Compose 自动初始化。

### 6. 常用命令
- 查看容器日志：
  ```bash
  docker compose logs
  ```
- 停止服务：
  ```bash
  docker compose down
  ```

## 依赖说明
- FastAPI
- Uvicorn
- SQLAlchemy
- mysqlclient
- sqlite3（标准库）

## 其它
- 脚本 `scripts/export_sqlite_utf8.py` 可自动导出 SQLite/MySQL 初始化 SQL，确保中文不乱码。
- 详细环境变量和敏感信息管理见 `.env` 文件。
