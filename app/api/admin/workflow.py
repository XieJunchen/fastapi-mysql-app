from fastapi import APIRouter, Request, Form, Depends, HTTPException
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
from sqlalchemy import text

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), '../../templates'))

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
    from app.crud.execute_record import get_user_count, get_task_count, get_status_count
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
    result_type: str = Form("image"),
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
        status=status,
        result_type=result_type
    )
    add_workflow(db, obj_in)
    return RedirectResponse(url="/admin/workflow", status_code=302)

@router.get("/admin/workflow/edit/{workflow_id}", response_class=HTMLResponse)
def admin_workflow_edit_form(workflow_id: int, request: Request, db: Session = Depends(get_db)):
    w = db.query(Workflow).filter_by(id=workflow_id).first()
    if not w:
        return "未找到"
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
    output_schema: str = Form(None),
    status: int = Form(1),
    result_type: str = Form("image"),
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
        status=status,
        result_type=result_type
    )
    from app.crud.workflow import update_workflow
    obj = update_workflow(db, workflow_id, update_dict)
    if not obj:
        raise HTTPException(status_code=404, detail="未找到")
    return RedirectResponse(url="/admin/workflow", status_code=302)

@router.get("/admin/workflow/delete/{workflow_id}")
def admin_workflow_delete(workflow_id: int, db: Session = Depends(get_db)):
    from app.crud.workflow import delete_workflow
    obj = delete_workflow(db, workflow_id)
    return RedirectResponse(url="/admin/workflow", status_code=302)

@router.get("/admin/workflow/detail/{workflow_id}", response_class=HTMLResponse)
def admin_workflow_detail(workflow_id: int, request: Request, db: Session = Depends(get_db)):
    w = db.query(Workflow).filter_by(id=workflow_id).first()
    if not w:
        return "未找到"
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
    try:
        data = json.loads(workflow)
        prompt = data.get("prompt", {})
        result = []
        for node_id, node in prompt.items():
            node_inputs = node.get("inputs", {})
            for k, v in node_inputs.items():
                param_type = type(v).__name__
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
