from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from sqlalchemy.exc import IntegrityError

def get_users(db: Session, skip: int = 0, limit: int = 10):
    return db.query(User).offset(skip).limit(limit).all()

def get_user_by_external(db: Session, source: str, external_user_id: str):
    return db.query(User).filter(User.source == source, User.external_user_id == external_user_id).first()

def create_user(db: Session, user: UserCreate):
    db_user = User(
        userId=user.userId,
        nickname=user.nickname,
        source=user.source,
        external_user_id=user.external_user_id,
        balance=user.balance
    )
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        return None
