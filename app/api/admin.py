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

# 已拆分，保留文件为空或仅保留必要的import
