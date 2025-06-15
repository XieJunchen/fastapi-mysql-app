from fastapi import FastAPI
from app.api import router as api_router
from app.db.database import engine, SessionLocal, DATABASE_URL
from app.models import Base, Workflow
from app.utils.config import load_config
import datetime
import json
import os
import subprocess
import sqlite3

app = FastAPI()

# 全局加载配置
config = load_config()

@app.on_event("startup")
def on_startup():
    # 开发环境：自动检测并初始化 SQLite 数据库
    if DATABASE_URL.startswith("sqlite"):
        db_path = DATABASE_URL.replace("sqlite:///./", "./").replace("sqlite:///", "")
        if not os.path.exists(db_path):
            sql_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "all_data_sqlite.sql")
            if os.path.exists(sql_path):
                print(f"[INFO] 未检测到 {db_path}，自动用 all_data_sqlite.sql 初始化数据库...")
                try:
                    # 纯 Python 方式初始化数据库
                    with open(sql_path, 'r', encoding='utf-8') as f:
                        sql_script = f.read()
                    conn = sqlite3.connect(db_path)
                    conn.executescript(sql_script)
                    conn.close()
                    print("[INFO] SQLite 数据库初始化完成！（Python 方式）")
                except Exception as e:
                    print(f"[ERROR] SQLite 初始化失败: {e}")
    Base.metadata.create_all(bind=engine)

app.include_router(api_router)