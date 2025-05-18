from sqlalchemy.orm import Session
from app.models import User, Workflow
from app.schemas import MyTableCreate
from .user import get_users
from .workflow import get_workflow_list, add_workflow, clear_workflow

def get_users(db: Session, skip: int = 0, limit: int = 10):
    return db.query(User).offset(skip).limit(limit).all()

# 查询全部
def get_workflow_list(db: Session, skip: int = 0, limit: int = 10):
    return db.query(Workflow).offset(skip).limit(limit).all()

# 创建一条记录
def add_workflow(db: Session, obj_in: MyTableCreate):
    db_obj = Workflow(**obj_in.dict())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj