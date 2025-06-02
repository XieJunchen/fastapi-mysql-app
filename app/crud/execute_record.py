from sqlalchemy.orm import Session
from app.models.execute_record import ExecuteRecord
import datetime

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
    record = db.query(ExecuteRecord).filter(ExecuteRecord.prompt_id == prompt_id).first()
    print(f"Updating record for prompt_id: {prompt_id}, status: {status}, result: {result}, messages: {messages}")
    if record:
        # 如果已是 finished 状态，不允许再更新为 failed 或其它状态
        if record.status == "finished":
            print(f"Record {prompt_id} is already finished, skip update.")
            return record
        record.status = status
        record.result = result
        record.execute_timeout = calculate_timeout(messages) if messages else None
        record.updated_time = datetime.datetime.utcnow()
        db.commit()
        db.refresh(record)
    return record

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
    print(f"Start Time: {startTime}, End Time: {endTime}")
    if startTime and endTime:
        total_time = (endTime - startTime) / 1000  # 转换为秒
    return total_time