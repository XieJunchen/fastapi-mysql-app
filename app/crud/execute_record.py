from sqlalchemy.orm import Session
from app.models.execute_record import ExecuteRecord
import datetime

def create_execute_record(db: Session, workflow_id: int, prompt_id: str, status: str = "pending", result=None, user_id=None):
    record = ExecuteRecord(
        workflow_id=workflow_id,
        prompt_id=prompt_id,
        status=status,
        result=result,
        created_time=datetime.datetime.utcnow(),
        updated_time=datetime.datetime.utcnow(),
        user_id=user_id
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def update_execute_record(db: Session, prompt_id: str, status: str, result=None):
    record = db.query(ExecuteRecord).filter(ExecuteRecord.prompt_id == prompt_id).first()
    if record:
        record.status = status
        record.result = result
        record.updated_time = datetime.datetime.utcnow()
        db.commit()
        db.refresh(record)
    return record

def get_execute_record(db: Session, prompt_id: str):
    return db.query(ExecuteRecord).filter(ExecuteRecord.prompt_id == prompt_id).first()

def get_user_count(db: Session):
    return db.query(ExecuteRecord.user_id).distinct().count()

def get_task_count(db: Session):
    return db.query(ExecuteRecord).count()

def get_status_count(db: Session, status: str):
    return db.query(ExecuteRecord).filter(ExecuteRecord.status == status).count()

def get_execute_record_list(db: Session, skip: int = 0, limit: int = 20, user_id: str = None, workflow_id: int = None, status: str = None):
    query = db.query(ExecuteRecord)
    if user_id:
        query = query.filter(ExecuteRecord.user_id == user_id)
    if workflow_id:
        query = query.filter(ExecuteRecord.workflow_id == workflow_id)
    if status:
        query = query.filter(ExecuteRecord.status == status)
    return query.order_by(ExecuteRecord.id.desc()).offset(skip).limit(limit).all()
