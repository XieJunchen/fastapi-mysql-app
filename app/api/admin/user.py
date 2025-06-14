from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from sqlalchemy import or_
from fastapi.templating import Jinja2Templates
import os
from decimal import Decimal

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), '../../templates'))

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
