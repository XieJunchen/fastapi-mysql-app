from fastapi import APIRouter, Request, Depends, Body
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.crud.execute_record import get_user_count, get_task_count, get_status_count, get_execute_record_list, update_execute_record_by_id
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

@router.post("/admin/execute_record/update")
def admin_update_execute_record(
    db: Session = Depends(get_db),
    data: dict = Body(...)
):
    """
    后台管理：根据id修改执行记录的状态、结果等字段
    {"id": 1, "status": "finished", "result": {...}, "execute_timeout": 12}
    """
    record_id = data.get("id")
    if not record_id:
        return JSONResponse({"msg": "缺少id"}, status_code=400)
    update_dict = {k: v for k, v in data.items() if k != "id"}
    record = update_execute_record_by_id(db, record_id, update_dict)
    if record:
        return {"msg": "更新成功", "record": {"id": record.id, "status": record.status, "result": record.result, "execute_timeout": record.execute_timeout}}
    else:
        return JSONResponse({"msg": "未找到记录或更新失败"}, status_code=404)
