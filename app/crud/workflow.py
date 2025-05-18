from sqlalchemy.orm import Session
from app.models import Workflow
from app.schemas import MyTableCreate

def get_workflow_list(db: Session, skip: int = 0, limit: int = 10):
    return db.query(Workflow).offset(skip).limit(limit).all()

def add_workflow(db: Session, obj_in: MyTableCreate):
    db_obj = Workflow(**obj_in.dict())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def clear_workflow(db: Session):
    db.query(Workflow).delete()
    db.commit()
