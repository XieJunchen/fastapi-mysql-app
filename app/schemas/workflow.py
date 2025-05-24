from pydantic import BaseModel
from typing import Optional, List
import datetime

class MyTableBase(BaseModel):
    name: str
    desc: Optional[str] = None
    useTimes: Optional[int] = 0
    workflow: Optional[str] = None
    picture: Optional[str] = None
    bigPicture: Optional[str] = None
    pictures: Optional[List[str]] = None
    flowType: Optional[str] = "local"
    input_schema: Optional[str] = None  # 新增字段
    output_schema: Optional[str] = None  # 新增字段
    status: Optional[int] = 1  # 1上线 0下线

class MyTableCreate(MyTableBase):
    pass

class MyTableOut(MyTableBase):
    id: int
    createdTime: datetime.datetime
    class Config:
        from_attributes = True
        json_encoders = {
            datetime.datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S') if v else None
        }
