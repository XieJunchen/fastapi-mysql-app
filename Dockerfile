# 基于官方 Python 镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt ./

# 安装系统依赖（mysqlclient 需要）
RUN apt-get update && apt-get install -y gcc default-libmysqlclient-dev pkg-config sqlite3 && rm -rf /var/lib/apt/lists/*

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 暴露端口（假设 FastAPI 运行在 8001）
EXPOSE 8001

# 启动命令（主入口应为 app.main:app）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
