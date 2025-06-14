from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.crud.execute_record import get_user_count, get_task_count, get_status_count, get_execute_record_list
from fastapi.templating import Jinja2Templates
import os

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), '../../templates'))

@router.get("/admin/execute_record", response_class=HTMLResponse)
def admin_execute_record_list(request: Request, db: Session = Depends(get_db), page: int = 1, size: int = 20, user_id: str = None, workflow_id: int = None, status: str = None):
    user_count = get_user_count(db)
    task_count = get_task_count(db)
    pending_count = get_status_count(db, "pending")
    finished_count = get_status_count(db, "finished")
    records = get_execute_record_list(db, skip=(page-1)*size, limit=size, user_id=user_id, workflow_id=workflow_id, status=status)
    total = get_task_count(db)  # 可根据筛选条件优化
    has_next = (page * size) < total
    return templates.TemplateResponse("execute_record_list.html", {
        "request": request,
        "records": records,
        "user_count": user_count,
        "task_count": task_count,
        "pending_count": pending_count,
        "finished_count": finished_count,
        "page": page,
        "size": size,
        "has_next": has_next,
        "user_id": user_id,
        "workflow_id": workflow_id,
        "status": status
    })
