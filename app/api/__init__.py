# This file is intentionally left blank.
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas import UserOut, MyTableOut, MyTableCreate
from app.crud import get_users, get_workflow_list, add_workflow
from app.models import Workflow

from .user import router as user_router
from .workflow import router as workflow_router
from .execute import router as execute_router
from .admin import router as admin_router

router = APIRouter()
router.include_router(user_router)
router.include_router(workflow_router)
router.include_router(execute_router)
router.include_router(admin_router)

@router.get("/users", response_model=list[UserOut])
def read_users_api(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return get_users(db, skip=skip, limit=limit)

@router.get("/workflow/list", response_model=list[MyTableOut])
def list_workflow_api(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return get_workflow_list(db, skip=skip, limit=limit)

@router.post("/workflow/add", response_model=MyTableOut)
def add_workflow_api(obj_in: MyTableCreate, db: Session = Depends(get_db)):
    return add_workflow(db, obj_in)

@router.delete("/workflow/clear", status_code=status.HTTP_204_NO_CONTENT)
def clear_workflow_api(db: Session = Depends(get_db)):
    db.query(Workflow).delete()
    db.commit()
    return

# 示例：如果有其他路由模块，可以在这里 include
# from . import user
# router.include_router(user.router)