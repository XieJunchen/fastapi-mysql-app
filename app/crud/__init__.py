from sqlalchemy.orm import Session
from app.models import User, Workflow
from app.schemas import MyTableCreate
from .user import get_users
from .workflow import get_workflow_list, add_workflow, clear_workflow
from .execute_record import create_execute_record, update_execute_record, get_execute_record

def get_users(db: Session, skip: int = 0, limit: int = 10):
    return db.query(User).offset(skip).limit(limit).all()