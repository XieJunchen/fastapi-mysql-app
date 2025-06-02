from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.dialects.sqlite import JSON
from app.db.database import Base
import datetime

class ExecuteRecord(Base):
    __tablename__ = "table_execute_record"
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, index=True)
    prompt_id = Column(String(100), index=True)
    status = Column(String(20), default="pending")  # pending, finished, failed
    result = Column(JSON, nullable=True)
    created_time = Column(DateTime, default=datetime.datetime.utcnow)
    updated_time = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    user_id = Column(String(64), index=True, nullable=True)  # 新增字段，记录执行人
    execute_timeout = Column(Integer, nullable=True)  # 执行耗时, 单位为秒
