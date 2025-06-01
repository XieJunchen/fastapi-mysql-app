from sqlalchemy import Column, Integer, String, DateTime, Numeric
from app.db.database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    userId = Column(String(64), unique=True, index=True, comment="用户ID，自动生成")
    nickname = Column(String(50), index=True, comment="昵称")
    source = Column(String(20), index=True, comment="账户来源")  # 抖音、快手等
    external_user_id = Column(String(64), index=True, comment="外部用户id")
    balance = Column(Numeric(12, 2), default=0.00, comment="账号余额")
    created_time = Column(DateTime, default=datetime.datetime.utcnow, comment="创建时间")
