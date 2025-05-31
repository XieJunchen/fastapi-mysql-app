from sqlalchemy.orm import Session
from app.models import Workflow
from app.schemas import MyTableCreate

def get_workflow_list(db: Session, skip: int = 0, limit: int = 10, status: int = None):
    query = db.query(Workflow)
    if status is not None:
        query = query.filter(Workflow.status == status)
    return query.offset(skip).limit(limit).all()

def add_workflow(db: Session, obj_in: MyTableCreate):
    db_obj = Workflow(**obj_in.dict())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def clear_workflow(db: Session):
    db.query(Workflow).delete()
    db.commit()

def update_workflow(db: Session, workflow_id: int, update_dict: dict):
    obj = db.query(Workflow).filter_by(id=workflow_id).first()
    if not obj:
        return None
    for k, v in update_dict.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

def delete_workflow(db: Session, workflow_id: int):
    obj = db.query(Workflow).filter_by(id=workflow_id).first()
    if obj:
        db.delete(obj)
        db.commit()
    return obj

def set_workflow_status(db: Session, workflow_id: int, status: int):
    obj = db.query(Workflow).filter_by(id=workflow_id).first()
    if not obj:
        return None
    obj.status = status
    db.commit()
    db.refresh(obj)
    return obj
