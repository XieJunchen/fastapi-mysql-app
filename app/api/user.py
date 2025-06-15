from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from sqlalchemy.orm import Session
import httpx
import json
import os
from app.db.database import get_db
from app.schemas.user import UserOut, UserCreate
from app.crud.user import get_users, get_user_by_external, create_user
from app.schemas.execute_record import ExecuteRecordOut
from app.crud.execute_record import get_execute_record_list
from app.models.user import User
from app.models.workflow import Workflow
from decimal import Decimal
from fastapi.responses import JSONResponse
from app.utils.config import load_config

router = APIRouter()

config_json = load_config()

def get_douyin_config():
    douyin_cfg = config_json.get('douyin', {})
    return douyin_cfg

@router.get("/users", response_model=list[UserOut])
def read_users_api(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return get_users(db, skip=skip, limit=limit)

@router.post("/users", response_model=UserOut)
def create_user_api(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_external(db, user.source, user.external_user_id)
    if db_user:
        return db_user
    db_user = create_user(db, user)
    if not db_user:
        raise HTTPException(status_code=400, detail="用户创建失败或已存在")
    return db_user

@router.post("/douyin/access_token")
def get_douyin_access_token():
    douyin_cfg = get_douyin_config()
    client_key = douyin_cfg.get('client_key')
    client_secret = douyin_cfg.get('client_secret')
    url = douyin_cfg.get('openapi_token_url')
    if not client_key or not client_secret:
        raise HTTPException(status_code=500, detail="Douyin client_key or client_secret not configured in config.json")
    headers = {"Content-Type": "application/json"}
    payload = {
        "grant_type": "client_credential",
        "client_key": client_key,
        "client_secret": client_secret
    }
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "access_token" in data:
            return {"access_token": data["access_token"]}
        else:
            raise HTTPException(status_code=400, detail=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/douyin/miniapp_access_token")
def get_douyin_miniapp_access_token():
    douyin_cfg = get_douyin_config()
    appid = douyin_cfg.get('AppID')
    secret = douyin_cfg.get('AppSecret')
    url = douyin_cfg.get('miniapp_token_url')
    if not appid or not secret:
        raise HTTPException(status_code=500, detail="Douyin AppID 或 AppSecret 未配置")
    headers = {"Content-Type": "application/json"}
    payload = {
        "appid": appid,
        "secret": secret,
        "grant_type": "client_credential"
    }
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "access_token" in data:
            return {"access_token": data["access_token"]}
        else:
            raise HTTPException(status_code=400, detail=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

### 异步创建用户
def async_create_user(source: str, openid: str):
    from app.db.database import SessionLocal
    from app.crud.user import get_user_by_external, create_user
    from app.schemas.user import UserCreate
    from sqlalchemy.exc import IntegrityError
    print(f"异步创建用户: source={source}, openid={openid}")
    db_async = SessionLocal()
    try:
        # 防重：先查是否已存在
        exist_user = get_user_by_external(db_async, source, openid)
        if exist_user:
            print(f"用户已存在: source={source}, external_user_id={openid}")
            return
        user_in = UserCreate(
            source=source,
            external_user_id=openid,
            nickname=openid
        )
        try:
            create_user(db_async, user_in)
        except IntegrityError:
            db_async.rollback()
            print(f"并发下唯一约束拦截，未重复创建: source={source}, external_user_id={openid}")
    finally:
        db_async.close()

### 获取抖音用户信息
@router.post("/douyin/login")
def douyin_login(
    db: Session = Depends(get_db), 
    background_tasks: BackgroundTasks = None, 
    params: dict = Body(default={})
):
    douyin_cfg = get_douyin_config()
    appid = douyin_cfg.get('AppID')
    secret = douyin_cfg.get('AppSecret')
    url = douyin_cfg.get('jscode2session_url')
    print(f"Douyin login params: {params}")
    code = params.get("code")
    if not appid or not secret:
        raise HTTPException(status_code=500, detail="Douyin AppID 或 AppSecret 未配置")
    params = {
        "appid": appid,
        "secret": secret,
        "code": code
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = httpx.post(url, json=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        openid = data.get("data").get("openid") if "data" in data else None
        if not openid:
            return data
        user = get_user_by_external(db, source="douyin", external_user_id=openid)
        if not user:
            if background_tasks is not None:
                background_tasks.add_task(async_create_user, source="douyin", openid=openid)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/profile")
def get_user_profile(
    userId: str = Query(None, description="用户ID"),
    source: str = Query(None, description="账户来源"),
    external_user_id: str = Query(None, description="外部用户id"),
    db: Session = Depends(get_db)
):
    user = None
    if userId:
        user = db.query(User).filter(User.userId == userId).first()
    elif source and external_user_id:
        user = get_user_by_external(db, source, external_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    avatar = getattr(user, 'avatar', '')
    return {
        "userId": user.userId,
        "nickname": user.nickname,
        "balance": str(user.balance) if user.balance is not None else "0.00",
        "photo": 'http://swqqsa5wv.hb-bkt.clouddn.com/admin/comfyui_85cc31c28dc44507b48405613872bf6c.png',
        "avatar": avatar
    }

def get_output_value(result_json):
    """
    从 result_json（str 或 dict）中提取 outputs 里的主要内容（支持图片、视频、文本等）
    返回 dict，包含所有类型的输出
    """
    if result_json is None:
        return None
    if isinstance(result_json, str):
        try:
            data = json.loads(result_json)
        except Exception:
            return None
    else:
        data = result_json
    if not isinstance(data, dict):
        return None
    outputs = data.get("outputs", {})
    # 常见类型字段
    result = {}
    if "image_url" in outputs:
        result["image_url"] = outputs["image_url"]
    if "video_url" in outputs:
        result["video_url"] = outputs["video_url"]
    if "text" in outputs:
        result["text"] = outputs["text"]
    # 其它类型可按需扩展
    return result

@router.get("/all/execute_records")
def get_all_execute_records(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    query = db.query(get_execute_record_list.__globals__['ExecuteRecord'])
    total = query.count()
    records = query.order_by(get_execute_record_list.__globals__['ExecuteRecord'].id.desc()).offset(skip).limit(limit).all()
    workflow_ids = list({r.workflow_id for r in records if r.workflow_id})
    user_ids = list({r.user_id for r in records if r.user_id})
    workflow_map = {}
    if workflow_ids:
        workflow_list = db.query(Workflow).filter(Workflow.id.in_(workflow_ids)).all()
        for wf in workflow_list:
            workflow_map[wf.id] = {
                "name": wf.name,
                "desc": wf.desc,
                "tags": getattr(wf, "tags", ["风景","AI","自然"]),
                "picture": getattr(wf, "picture", ""),
                "category": getattr(wf, "flowType", "")
            }
    user_map = {user.id: user for user in db.query(User).filter(User.id.in_(user_ids)).all()}
    result = []
    for r in records:
        output_value = get_output_value(r.result) if r.result else None
        if not output_value:
            continue
        workflow_info = workflow_map.get(r.workflow_id, {"name": "", "desc": "", "tags": [], "picture": "", "category": ""})
        user = user_map.get(r.user_id)
        result.append({
            "author": {
                "avatar": "http://swqqsa5wv.hb-bkt.clouddn.com/admin/comfyui_85cc31c28dc44507b48405613872bf6c.png",  # 你的 user 没有头像字段
                "id": r.user_id or "",
                "name": user.nickname if user else "张三"
            },
            "category": workflow_info["category"] or "",
            "description": workflow_info["desc"] or "",
            "id": str(r.id),
            "imageUrl": output_value["image_url"] or "",
            "likes": 0,  # 没有 likes 字段，默认 0
            "tags": workflow_info["tags"] or [],
            "title": workflow_info["name"] or "",
            "views": 0  # 没有 views 字段，默认 0
        })
    return JSONResponse(content={"total": total, "items": result})

@router.get("/user/execute_records", response_model=list[ExecuteRecordOut])
def get_user_execute_records(
    userId: str = Query(None, description="用户ID"),
    source: str = Query(None, description="账户来源"),
    external_user_id: str = Query(None, description="外部用户id"),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    user = None
    if userId:
        user = db.query(User).filter(User.userId == userId).first()
    elif source and external_user_id:
        user = get_user_by_external(db, source, external_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    query = db.query(get_execute_record_list.__globals__['ExecuteRecord']).filter(get_execute_record_list.__globals__['ExecuteRecord'].user_id == user.userId)
    total = query.count()
    records = query.order_by(get_execute_record_list.__globals__['ExecuteRecord'].id.desc()).offset(skip).limit(limit).all()
    result = []
    for r in records:
        consume_amount = None
        if r.result and isinstance(r.result, dict):
            consume_amount = r.result.get('consume_amount', 0.0)
        output_value = get_output_value(r.result) if r.result else None
        if not output_value:
            continue  # 如果没有图片链接，则跳过该记录
        result.append({
            "id": r.id,
            "workflow_id": r.workflow_id,
            "user_id": r.user_id,
            "created_time": r.created_time.strftime('%Y-%m-%d %H:%M:%S') if r.created_time else None,
            "execute_timeout": r.execute_timeout,
            "result": r.result,
            "status": r.status,
            "output": output_value,
            "consume_amount": consume_amount
        })
    return JSONResponse(content={"total": total, "items": result})

# 工具函数，避免重复代码

def build_execute_record_result(records, db):
    workflow_ids = list({r.workflow_id for r in records if r.workflow_id})
    workflow_map = {}
    if workflow_ids:
        workflow_list = db.query(Workflow).filter(Workflow.id.in_(workflow_ids)).all()
        for wf in workflow_list:
            workflow_map[wf.id] = {
                "name": wf.name,
                "desc": wf.desc,
                "tags": getattr(wf, "tags", None)
            }
    user_ids = list({r.user_id for r in records if r.user_id})
    user_map = {}
    if user_ids:
        user_list = db.query(User).filter(User.id.in_(user_ids)).all()
        for u in user_list:
            user_map[u.id] = u.nickname
    result = []
    for r in records:
        consume_amount = None
        if r.result and isinstance(r.result, dict):
            consume_amount = r.result.get('consume_amount', 0.0)
        output_value = get_output_value(r.result) if r.result else None
        if not output_value:
            continue
        workflow_info = workflow_map.get(r.workflow_id, {"name": None, "desc": None, "tags": None})
        nickname = user_map.get(r.user_id)
        result.append({
            "id": r.id,
            "workflow_id": r.workflow_id,
            "user_id": r.user_id,
            "user_nickname": nickname,
            "created_time": r.created_time.strftime('%Y-%m-%d %H:%M:%S') if r.created_time else None,
            "execute_timeout": r.execute_timeout,
            "result": r.result,
            "status": r.status,
            "output": output_value,
            "consume_amount": consume_amount,
            "workflow_name": workflow_info["name"],
            "workflow_desc": workflow_info["desc"],
            "workflow_tags": workflow_info["tags"]
        })
    return result