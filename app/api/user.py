from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas import UserOut
from app.crud import get_users

router = APIRouter()

@router.get("/users", response_model=list[UserOut])
def read_users_api(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return get_users(db, skip=skip, limit=limit)
