from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import httpx
import json
import os

from app.db.database import get_db
from app.schemas import UserOut
from app.crud import get_users

router = APIRouter()

@router.get("/users", response_model=list[UserOut])
def read_users_api(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return get_users(db, skip=skip, limit=limit)

def get_douyin_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    douyin_cfg = config.get('douyin', {})
    return douyin_cfg

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

@router.get("/douyin/jscode2session")
def douyin_jscode2session(code: str = Query(..., description="前端获取的 code")):
    douyin_cfg = get_douyin_config()
    appid = douyin_cfg.get('AppID')
    secret = douyin_cfg.get('AppSecret')
    url = douyin_cfg.get('jscode2session_url')
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
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))