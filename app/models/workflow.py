from sqlalchemy import Column, Integer, String, DateTime, Text
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
    input_schema = Column(Text, nullable=True)  # 新增字段，存储输入参数定义
    output_schema = Column(Text, nullable=True)  # 新增字段，存储输出参数定义
    status = Column(Integer, default=1, nullable=False, comment="1上线 0下线")
    result_type = Column(String(20), default="image", comment="结果类型：image图片、video视频、text文字等")  # 新增字段
