from pydantic import BaseModel
from typing import Optional, Any
import datetime

class ExecuteRecordOut(BaseModel):
    id: int
    user_id: Optional[str]
    created_time: datetime.datetime
    execute_timeout: Optional[float]  # 修正为 float
    result: Any
    status: str
    # 消耗金额字段，假设为consume_amount，后续接口中处理
    consume_amount: Optional[float] = None

    class Config:
        orm_mode = True
