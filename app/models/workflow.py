from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.sqlite import JSON
from app.db.database import Base
import datetime

class Workflow(Base):
    __tablename__ = "table_workflow"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    desc = Column(String(255))
    useTimes = Column(Integer, default=0)
    workflow = Column(String(255))
    createdTime = Column(DateTime, default=datetime.datetime.utcnow)
    picture = Column(String(255))
    bigPicture = Column(String(255))
    pictures = Column(JSON)
    flowType = Column(String(50), default="local")
