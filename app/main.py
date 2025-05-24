from fastapi import FastAPI
from app.api import router as api_router
from app.db.database import engine, SessionLocal
from app.models import Base, Workflow
import datetime
import json
import os

app = FastAPI()

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if db.query(Workflow).count() == 0:
        # 从 db_init.json 读取数据
        json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db_init.json")
        with open(json_path, "r", encoding="utf-8") as f:
            workflows = json.load(f)
        for w in workflows:
            # 处理 createdTime 字段
            if "createdTime" in w and w["createdTime"]:
                try:
                    from datetime import datetime
                    w["createdTime"] = datetime.strptime(w["createdTime"], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    w["createdTime"] = datetime.now()
            # 处理 pictures 字段
            if "pictures" in w and isinstance(w["pictures"], str):
                try:
                    w["pictures"] = json.loads(w["pictures"])
                except Exception:
                    w["pictures"] = []
            db.add(Workflow(**w))
        db.commit()
    db.close()
    

app.include_router(api_router)