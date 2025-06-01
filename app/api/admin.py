from fastapi import APIRouter, Request, Form, Depends, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models import Workflow
from app.schemas.workflow import MyTableCreate
from fastapi.templating import Jinja2Templates
import os
import json
from typing import List
from app.crud.workflow import add_workflow, update_workflow, delete_workflow, set_workflow_status
from app.crud.execute_record import get_user_count, get_task_count, get_status_count, get_execute_record_list
from app.models.execute_record import ExecuteRecord
from app.models.user import User
from app.crud.user import get_users
from sqlalchemy import or_
from fastapi import Form
from decimal import Decimal
from app.crud.user import get_user_by_external

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), '../templates'))

# 管理首页-列表
@router.get("/admin/workflow", response_class=HTMLResponse)
def admin_workflow_list(request: Request, db: Session = Depends(get_db)):
    q = request.query_params.get('q', '').strip()
    page = int(request.query_params.get('page', 1))
    size = int(request.query_params.get('size', 10))
    query = db.query(Workflow)
    if q:
        query = query.filter((Workflow.name.contains(q)) | (Workflow.flowType.contains(q)))
    total = query.count()
    workflows = query.order_by(Workflow.id.desc()).offset((page-1)*size).limit(size).all()
    has_next = (page * size) < total
    # 统计区块数据
    user_count = get_user_count(db)
    task_count = get_task_count(db)
    pending_count = get_status_count(db, "pending")
    finished_count = get_status_count(db, "finished")
    return templates.TemplateResponse("workflow_list.html", {
        "request": request,
        "workflows": workflows,
        "q": q,
        "page": page,
        "size": size,
        "has_next": has_next,
        "user_count": user_count,
        "task_count": task_count,
        "pending_count": pending_count,
        "finished_count": finished_count
    })

# 新增页面
@router.get("/admin/workflow/add", response_class=HTMLResponse)
def admin_workflow_add_form(request: Request):
    return templates.TemplateResponse("workflow_form.html", {
        "request": request,
        "w": None,
        "form_action": "/admin/workflow/add",
        "form_title": "新增工作流",
        "submit_text": "提交"
    })

@router.post("/admin/workflow/add")
def admin_workflow_add(
    name: str = Form(...),
    flowType: str = Form(...),
    desc: str = Form(""),
    picture: str = Form(""),
    bigPicture: str = Form(""),
    pictures: List[str] = Form([]),
    workflow: str = Form(""),
    input_schema: str = Form(None),
    output_schema: str = Form(None),
    status: int = Form(1),
    db: Session = Depends(get_db)
):
    obj_in = MyTableCreate(
        name=name,
        flowType=flowType,
        desc=desc,
        picture=picture,
        bigPicture=bigPicture,
        pictures=[p.strip() for p in pictures if p.strip()],
        workflow=workflow,
        input_schema=input_schema,
        output_schema=output_schema,
        status=status
    )
    add_workflow(db, obj_in)
    return RedirectResponse(url="/admin/workflow", status_code=302)

# 编辑页面
@router.get("/admin/workflow/edit/{workflow_id}", response_class=HTMLResponse)
def admin_workflow_edit_form(workflow_id: int, request: Request, db: Session = Depends(get_db)):
    w = db.query(Workflow).filter_by(id=workflow_id).first()
    if not w:
        return "未找到"
    # 保证 w.pictures 为 list 且每个元素为非空字符串
    if isinstance(w.pictures, str):
        try:
            w.pictures = json.loads(w.pictures)
        except Exception:
            w.pictures = []
    if not isinstance(w.pictures, list):
        w.pictures = []
    w.pictures = [p for p in w.pictures if isinstance(p, str) and p.strip()]
    return templates.TemplateResponse("workflow_form.html", {
        "request": request,
        "w": w,
        "form_action": f"/admin/workflow/edit/{workflow_id}",
        "form_title": "编辑工作流",
        "submit_text": "保存修改"
    })

# 编辑
@router.post("/admin/workflow/edit/{workflow_id}")
def admin_workflow_edit(
    workflow_id: int,
    name: str = Form(...),
    flowType: str = Form(...),
    desc: str = Form(""),
    picture: str = Form(""),
    bigPicture: str = Form(""),
    pictures: List[str] = Form([]),
    workflow: str = Form(""),
    input_schema: str = Form(None),
    output_schema: str = Form(None),
    status: int = Form(1),
    db: Session = Depends(get_db)
):
    update_dict = dict(
        name=name,
        flowType=flowType,
        desc=desc,
        picture=picture,
        bigPicture=bigPicture,
        pictures=[p.strip() for p in pictures if p.strip()],
        workflow=workflow,
        input_schema=input_schema,
        output_schema=output_schema,
        status=status
    )
    obj = update_workflow(db, workflow_id, update_dict)
    if not obj:
        raise HTTPException(status_code=404, detail="未找到")
    return RedirectResponse(url="/admin/workflow", status_code=302)

# 删除
@router.get("/admin/workflow/delete/{workflow_id}")
def admin_workflow_delete(workflow_id: int, db: Session = Depends(get_db)):
    obj = delete_workflow(db, workflow_id)
    return RedirectResponse(url="/admin/workflow", status_code=302)

# 详情
@router.get("/admin/workflow/detail/{workflow_id}", response_class=HTMLResponse)
def admin_workflow_detail(workflow_id: int, request: Request, db: Session = Depends(get_db)):
    w = db.query(Workflow).filter_by(id=workflow_id).first()
    if not w:
        return "未找到"
    # 保证 w.pictures 为 list 且每个元素为非空字符串
    if isinstance(w.pictures, str):
        try:
            w.pictures = json.loads(w.pictures)
        except Exception:
            w.pictures = []
    if not isinstance(w.pictures, list):
        w.pictures = []
    w.pictures = [p for p in w.pictures if isinstance(p, str) and p.strip()]
    return templates.TemplateResponse("workflow_detail.html", {"request": request, "w": w})

@router.post("/admin/workflow/online/{workflow_id}")
def admin_workflow_online(workflow_id: int, db: Session = Depends(get_db)):
    obj = set_workflow_status(db, workflow_id, 1)
    if not obj:
        raise HTTPException(status_code=404, detail="未找到")
    return RedirectResponse(url="/admin/workflow", status_code=302)

@router.post("/admin/workflow/offline/{workflow_id}")
def admin_workflow_offline(workflow_id: int, db: Session = Depends(get_db)):
    obj = set_workflow_status(db, workflow_id, 0)
    if not obj:
        raise HTTPException(status_code=404, detail="未找到")
    return RedirectResponse(url="/admin/workflow", status_code=302)

@router.post("/admin/workflow/prompt_params")
def get_prompt_params(workflow: str = Form(...)):
    """解析 workflow 字段中的 prompt，仅返回输入参数树结构（不生成 outputs）"""
    import json
    try:
        data = json.loads(workflow)
        prompt = data.get("prompt", {})
        result = []
        for node_id, node in prompt.items():
            node_inputs = node.get("inputs", {})
            for k, v in node_inputs.items():
                param_type = type(v).__name__
                # 类型映射：只允许 IMG/STR/VIDEO
                if param_type.lower() == 'str':
                    mapped_type = 'STR'
                elif param_type.lower() == 'list' and k.lower() == 'images':
                    mapped_type = 'IMG'
                elif param_type.lower() == 'dict' and k.lower() == 'video':
                    mapped_type = 'VIDEO'
                else:
                    mapped_type = 'STR'
                result.append({
                    "node_id": node_id,
                    "node_type": node.get("class_type", ""),
                    "param": k,
                    "value": v,
                    "type": mapped_type,
                    "path": f"{node_id}.inputs.{k}",
                    "title": node.get("_meta", {}).get("title", "")
                })
        return JSONResponse(content={"params": {"inputs": result}})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)

# 执行记录统计和列表
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

@router.get("/admin/user", response_class=HTMLResponse)
def admin_user_list(request: Request, db: Session = Depends(get_db)):
    q = request.query_params.get('q', '').strip()
    page = int(request.query_params.get('page', 1))
    size = int(request.query_params.get('size', 20))
    query = db.query(User)
    if q:
        query = query.filter(
            or_(
                User.nickname.contains(q),
                User.source.contains(q),
                User.external_user_id.contains(q),
                User.userId.contains(q)
            )
        )
    total = query.count()
    users = query.order_by(User.id.desc()).offset((page-1)*size).limit(size).all()
    has_next = (page * size) < total
    return templates.TemplateResponse("user_list.html", {
        "request": request,
        "users": users,
        "q": q,
        "page": page,
        "size": size,
        "has_next": has_next
    })

@router.post("/admin/user/deduct/{user_id}")
def admin_user_deduct(user_id: int, amount: float = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if amount <= 0 or user.balance < Decimal(str(amount)):
        return RedirectResponse(url="/admin/user", status_code=302)
    user.balance = user.balance - Decimal(str(amount))
    db.commit()
    return RedirectResponse(url="/admin/user", status_code=302)
