from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from app.db.database import get_db
from app.models.execute_record import ExecuteRecord
from app.models import Workflow, User
from app.crud.execute_record import (
    update_execute_record_by_id,
    delete_execute_record_by_id,
    get_execute_record_list,
)
from app.crud.user import get_user_by_external
from app.api.user import get_output_value
from app.schemas.execute_record import ExecuteRecordOut
import random

router = APIRouter()


@router.post("/record/{record_id}/publish")
def publish_execute_record(record_id: int, db: Session = Depends(get_db)):
    """切换 is_public 字段（0/1），实现发布/取消发布。"""
    record = db.query(ExecuteRecord).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    new_is_public = 0 if record.is_public else 1
    update_execute_record_by_id(db, record_id, {"is_public": new_is_public})
    return {
        "msg": "发布状态已切换",
        "record_id": record_id,
        "is_public": new_is_public,
    }


@router.delete("/record/{record_id}")
def delete_execute_record(record_id: int, db: Session = Depends(get_db)):
    """删除执行记录。"""
    success = delete_execute_record_by_id(db, record_id)
    if not success:
        raise HTTPException(status_code=404, detail="记录不存在或已删除")
    return {"msg": "记录已删除", "record_id": record_id}


@router.get("/record/{record_id}")
def get_record(record_id: int, db: Session = Depends(get_db)):
    """查询单条执行记录（按id）"""
    record = db.query(ExecuteRecord).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record


@router.get("/record/list")
def list_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user_id: str = None,
    workflow_id: int = None,
    status: str = None,
    db: Session = Depends(get_db),
):
    """分页查询执行记录列表，支持筛选"""
    records = get_execute_record_list(
        db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        workflow_id=workflow_id,
        status=status,
    )
    return records


@router.post("/admin/execute_record/update")
def update_execute_record(
    data: dict = Body(...),
    db: Session = Depends(get_db),
):
    """编辑执行记录，支持 status、execute_timeout、result 字段。"""
    record_id = data.get("id")
    if not record_id:
        raise HTTPException(status_code=400, detail="缺少id")
    update_data = {}
    for field in ["status", "execute_timeout", "result"]:
        if field in data:
            update_data[field] = data[field]
    if not update_data:
        raise HTTPException(status_code=400, detail="没有可更新字段")
    success = update_execute_record_by_id(db, record_id, update_data)
    if not success:
        raise HTTPException(status_code=404, detail="记录不存在或更新失败")
    return {"msg": "更新成功", "record_id": record_id}


@router.get("/all/execute_records")
def get_all_execute_records(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    query = db.query(ExecuteRecord).filter(ExecuteRecord.is_public == 1)
    total = query.count()
    records = query.order_by(ExecuteRecord.id.desc()).offset(skip).limit(limit).all()
    workflow_ids = list({r.workflow_id for r in records if r.workflow_id})
    user_ids = list({r.user_id for r in records if r.user_id})
    workflow_map = {}
    if workflow_ids:
        workflow_list = db.query(Workflow).filter(Workflow.id.in_(workflow_ids)).all()
        for wf in workflow_list:
            workflow_map[wf.id] = {
                "name": wf.name,
                "desc": wf.desc,
                "tags": getattr(wf, "tags", ["风景", "AI", "自然"]),
                "picture": getattr(wf, "picture", ""),
                "category": getattr(wf, "flowType", ""),
                "result_type": getattr(wf, "result_type", "text")
            }
    user_map = {user.id: user for user in db.query(User).filter(User.id.in_(user_ids)).all()}
    result = []
    for r in records:
        output_value = get_output_value(r.result) if r.result else None
        if not output_value:
            continue
        workflow_info = workflow_map.get(
            r.workflow_id,
            {"name": "", "desc": "", "tags": [], "picture": "", "category": ""},
        )
        user = user_map.get(r.user_id)
        result.append(
            {
                "author": {
                    "avatar": "http://swqqsa5wv.hb-bkt.clouddn.com/admin/comfyui_85cc31c28dc44507b48405613872bf6c.png",
                    "id": r.user_id or "",
                    "name": user.nickname if user else "张三",
                },
                "category": workflow_info["category"] or "",
                "description": workflow_info["desc"] or "",
                "id": str(r.id),
                "imageUrl": output_value["image_url"] or "",
                "likes": random.randint(0, 1000),
                "tags": workflow_info["tags"] or [],
                "title": workflow_info["name"] or "",
                "result_type": workflow_info["result_type"] or "",
                "views": random.randint(0, 1000)
            }
        )
    return JSONResponse(content={"total": total, "items": result})


@router.get("/user/execute_records", response_model=list[ExecuteRecordOut])
def get_user_execute_records(
    userId: str = Query(None, description="用户ID"),
    source: str = Query(None, description="账户来源"),
    external_user_id: str = Query(None, description="外部用户id"),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    user = None
    if userId:
        user = db.query(User).filter(User.userId == userId).first()
    elif source and external_user_id:
        user = get_user_by_external(db, source, external_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    query = db.query(ExecuteRecord).filter(ExecuteRecord.user_id == user.userId)
    total = query.count()
    records = query.order_by(ExecuteRecord.id.desc()).offset(skip).limit(limit).all()
    result = []
    for r in records:
        consume_amount = None
        if r.result and isinstance(r.result, dict):
            consume_amount = r.result.get("consume_amount", 0.0)
        output_value = get_output_value(r.result) if r.result else None
        if not output_value:
            continue
        result.append(
            {
                "id": r.id,
                "workflow_id": r.workflow_id,
                "user_id": r.user_id,
                "created_time": r.created_time.strftime("%Y-%m-%d %H:%M:%S") if r.created_time else None,
                "execute_timeout": r.execute_timeout,
                "result": r.result,
                "status": r.status,
                "output": output_value,
                "consume_amount": consume_amount,
            }
        )
    return JSONResponse(content={"total": total, "items": result})
