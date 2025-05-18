from sqlalchemy.orm import Session
from app.models import User

def get_users(db: Session, skip: int = 0, limit: int = 10):
    return db.query(User).offset(skip).limit(limit).all()
