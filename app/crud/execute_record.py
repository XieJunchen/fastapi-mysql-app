from sqlalchemy.orm import Session
from app.models.execute_record import ExecuteRecord
import datetime
from app.utils.logger import logger

def create_execute_record(db: Session, workflow_id: int, prompt_id: str, status: str = "pending", result=None, user_id=None, execute_timeout=None):
    record = ExecuteRecord(
        workflow_id=workflow_id,
        prompt_id=prompt_id,
        status=status,
        result=result,
        created_time=datetime.datetime.utcnow(),
        updated_time=datetime.datetime.utcnow(),
        user_id=user_id,
        execute_timeout=execute_timeout
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def update_execute_record(db: Session, prompt_id: str, status: str, result=None, messages=None):
    # 只更新未 finished 的记录，防止并发覆盖
    now = datetime.datetime.utcnow()
    execute_timeout = calculate_timeout(messages) if messages else None
    update_data = {
        'status': status,
        'result': result,
        'execute_timeout': execute_timeout,
        'updated_time': now
    }
    rows = db.query(ExecuteRecord).filter(ExecuteRecord.prompt_id == prompt_id, ExecuteRecord.status != "finished").update(update_data)
    if rows:
        db.commit()
        record = db.query(ExecuteRecord).filter(ExecuteRecord.prompt_id == prompt_id).first()
        logger.info(f"[更新记录] prompt_id={prompt_id} 状态已更新为{status}")
        return record
    else:
        record = db.query(ExecuteRecord).filter(ExecuteRecord.prompt_id == prompt_id).first()
        logger.info(f"[更新记录] prompt_id={prompt_id} 已是finished或不存在，跳过更新")
        return record

def update_execute_record_by_id(db: Session, record_id: int, update_dict: dict):
    """
    根据主键ID直接修改执行记录的任意字段（如状态、结果等），不限制 status 是否为 finished。
    适合后台或管理员操作。
    """
    record = db.query(ExecuteRecord).filter(ExecuteRecord.id == record_id).first()
    if not record:
        logger.info(f"[更新记录] id={record_id} 不存在，无法更新")
        return None
    for k, v in update_dict.items():
        if k == 'execute_timeout' and v is not None:
            try:
                v = int(float(v))  # 支持小数转为整数秒
            except Exception:
                v = 0
        setattr(record, k, v)
    record.updated_time = datetime.datetime.utcnow()
    db.commit()
    db.refresh(record)
    logger.info(f"[更新记录] id={record_id} 字段已更新: {update_dict}")
    return record

def delete_execute_record_by_id(db: Session, record_id: int):
    """根据主键ID删除执行记录。"""
    record = db.query(ExecuteRecord).filter(ExecuteRecord.id == record_id).first()
    if not record:
        logger.info(f"[删除记录] id={record_id} 不存在，无法删除")
        return False
    db.delete(record)
    db.commit()
    logger.info(f"[删除记录] id={record_id} 已删除")
    return True

def get_execute_record(db: Session, prompt_id: str):
    return db.query(ExecuteRecord).filter(ExecuteRecord.prompt_id == prompt_id).first()

def get_user_count(db: Session):
    return db.query(ExecuteRecord.user_id).distinct().count()

def get_task_count(db: Session):
    return db.query(ExecuteRecord).count()

def get_status_count(db: Session, status: str):
    return db.query(ExecuteRecord).filter(ExecuteRecord.status == status).count()

def get_execute_record_list(db: Session, skip: int = 0, limit: int = 20, user_id: str = None, workflow_id: int = None, status: str = None):
    query = db.query(ExecuteRecord)
    if user_id:
        query = query.filter(ExecuteRecord.user_id == user_id)
    if workflow_id:
        query = query.filter(ExecuteRecord.workflow_id == workflow_id)
    if status:
        query = query.filter(ExecuteRecord.status == status)
    return query.order_by(ExecuteRecord.id.desc()).offset(skip).limit(limit).all()

### 计算执行时间
def calculate_timeout(messages):
    total_time = 10 # 默认超时时间为10秒
    if not messages:
        return total_time
    startTime = None
    endTime = None
    for item in messages:
        if len(item) >= 2:
            if item[0] == "execution_start":
                startTime = item[1].get("timestamp")
            elif item[0] == "execution_success":
                endTime = item[1].get("timestamp")
    if startTime and endTime:
        total_time = (endTime - startTime) / 1000  # 转换为秒
    return total_time