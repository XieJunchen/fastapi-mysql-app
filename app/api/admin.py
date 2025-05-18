from fastapi import APIRouter, Request, Form, Depends, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models import Workflow
from app.schemas.workflow import MyTableCreate
from fastapi.templating import Jinja2Templates
import os
import json
from typing import List

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
    return templates.TemplateResponse("workflow_list.html", {
        "request": request,
        "workflows": workflows,
        "q": q,
        "page": page,
        "size": size,
        "has_next": has_next
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
    db: Session = Depends(get_db)
):
    obj = Workflow(
        name=name,
        flowType=flowType,
        desc=desc,
        picture=picture,
        bigPicture=bigPicture,
        pictures=[p.strip() for p in pictures if p.strip()],
        workflow=workflow,
        input_schema=input_schema
    )
    db.add(obj)
    db.commit()
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
    db: Session = Depends(get_db)
):
    w = db.query(Workflow).filter_by(id=workflow_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="未找到")
    w.name = name
    w.flowType = flowType
    w.desc = desc
    w.picture = picture
    w.bigPicture = bigPicture
    w.pictures = [p.strip() for p in pictures if p.strip()]
    w.workflow = workflow
    w.input_schema = input_schema
    db.commit()
    return RedirectResponse(url="/admin/workflow", status_code=302)

# 删除
@router.get("/admin/workflow/delete/{workflow_id}")
def admin_workflow_delete(workflow_id: int, db: Session = Depends(get_db)):
    w = db.query(Workflow).filter_by(id=workflow_id).first()
    if w:
        db.delete(w)
        db.commit()
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
