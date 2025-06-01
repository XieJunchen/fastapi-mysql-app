from pydantic import BaseModel, root_validator
from typing import Optional
from decimal import Decimal
import datetime
import random

class UserBase(BaseModel):
    nickname: str
    source: str
    external_user_id: str
    balance: Decimal = 10.00
    userId: Optional[str] = None  # 新增 userId 字段

class UserCreate(UserBase):
    id: Optional[int] = None

    @root_validator(pre=True)
    def auto_fill_fields(cls, values):
        # 自动生成 userId
        if not values.get('userId'):
            now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            rand = str(random.randint(10000, 99999))
            values['userId'] = f"U{now}{rand}"
        # 自动生成昵称
        if not values.get('nickname'):
            values['nickname'] = 'AIGC-' + values['userId']
        # 自动设置余额
        if not values.get('balance'):
            values['balance'] = Decimal('10.00')
        return values

class UserOut(UserBase):
    id: int
    created_time: datetime.datetime
    class Config:
        orm_mode = True
