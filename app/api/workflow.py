from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas import MyTableOut, MyTableCreate
from app.crud import get_workflow_list, add_workflow, clear_workflow
from app.models import Workflow

router = APIRouter()

@router.get("/workflow/list", response_model=list[MyTableOut])
def list_workflow_api(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return get_workflow_list(db, skip=skip, limit=limit, status=1)

@router.post("/workflow/add", response_model=MyTableOut)
def add_workflow_api(obj_in: MyTableCreate, db: Session = Depends(get_db)):
    return add_workflow(db, obj_in)

@router.delete("/workflow/clear", status_code=status.HTTP_204_NO_CONTENT)
def clear_workflow_api(db: Session = Depends(get_db)):
    clear_workflow(db)
    return

@router.get("/workflow/detail/{workflow_id}", response_model=MyTableOut)
def get_workflow_detail(workflow_id: int, db: Session = Depends(get_db)):
    obj = db.query(Workflow).filter_by(id=workflow_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return obj

@router.post("/workflow/online/{workflow_id}")
def online_workflow(workflow_id: int, db: Session = Depends(get_db)):
    obj = db.query(Workflow).filter_by(id=workflow_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Workflow not found")
    obj.status = 1
    db.commit()
    return {"msg": "已上线", "id": workflow_id}

@router.post("/workflow/offline/{workflow_id}")
def offline_workflow(workflow_id: int, db: Session = Depends(get_db)):
    obj = db.query(Workflow).filter_by(id=workflow_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Workflow not found")
    obj.status = 0
    db.commit()
    return {"msg": "已下线", "id": workflow_id}
