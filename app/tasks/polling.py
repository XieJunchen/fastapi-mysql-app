import threading
import time
import json
import requests
from sqlalchemy import desc
from app.db.database import SessionLocal
from app.crud.execute_record import get_execute_record_list, update_execute_record
from app.models.workflow import Workflow
from app.utils.logger import logger

# 全局定时任务控制变量
polling_thread = None
polling_thread_lock = threading.Lock()

def get_comfyui_history(COMFYUI_API_HISTORY):
    try:
        resp = requests.get(COMFYUI_API_HISTORY, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.warning(f'[定时任务] 请求API失败，状态码: {resp.status_code}')
            return None
    except Exception as e:
        logger.error(f"[定时任务] comfyUI history 批量同步异常: {e}")
        return None

def sync_prompts_to_db(db, prompt_items):
    # prompt_items: List[(pid, item)]
    update_list = []
    for pid, item in prompt_items:
        outputs = item.get('outputs')
        messages = item.get('status', {}).get('messages', [])
        if outputs:
            rec = db.query(get_execute_record_list.__globals__['ExecuteRecord']).filter_by(prompt_id=pid).first()
            if rec and rec.status != "finished":
                # 新增：查 workflow_id，查 workflow，取 output_schema，标准化 outputs
                workflow_id = rec.workflow_id
                workflow_db = db.query(Workflow).filter(Workflow.id == workflow_id).first() if workflow_id else None
                output_schema = None
                if workflow_db and getattr(workflow_db, 'output_schema', None):
                    try:
                        output_schema = json.loads(workflow_db.output_schema) if isinstance(workflow_db.output_schema, str) else workflow_db.output_schema
                    except Exception:
                        output_schema = None
                # 导入 parse_outputs_from_schema
                from app.api.execute import parse_outputs_from_schema
                std_outputs = parse_outputs_from_schema(outputs, output_schema)
                if std_outputs:
                    update_list.append((pid, std_outputs, messages))
    # 批量更新
    for pid, std_outputs, messages in update_list:
        update_execute_record(db, pid, status="finished", result={"outputs": std_outputs}, messages=messages)
    if update_list:
        db.commit()
        logger.info(f"[定时任务] 本次批量同步 {len(update_list)} 条prompt记录, update_list:{update_list}")

def poll_latest_prompt_result():
    empty_count = 0  # 连续无待处理记录的计数
    max_empty_count = 10  # 阈值，连续10次无记录则自动退出
    from app.api.execute import COMFYUI_API_HISTORY  # 避免循环引用
    db = SessionLocal()
    try:
        while True:
            data = get_comfyui_history(COMFYUI_API_HISTORY)
            if data:
                prompt_items = list(data.items())
                sync_prompts_to_db(db, prompt_items)
                empty_count = 0
            else:
                empty_count += 1
                logger.info(f'[定时任务] 暂无待处理的prompt记录，已连续{empty_count}次')
                if empty_count >= max_empty_count:
                    logger.info(f'[定时任务] 连续{max_empty_count}次无待处理记录，自动退出轮询线程')
                    break
            # 指数级延迟，避免空转浪费资源
            delay = min(2 ** empty_count, 300)  # 最大延迟限制为5分钟
            time.sleep(delay)
    finally:
        db.close()
        logger.info('[定时任务] 数据库连接已关闭')

def start_polling_if_needed():
    global polling_thread
    with polling_thread_lock:
        if polling_thread is None or not polling_thread.is_alive():
            logger.info('[定时任务] 线程未启动，准备启动...')
            polling_thread = threading.Thread(target=poll_latest_prompt_result, daemon=True)
            polling_thread.start()
            logger.info('[定时任务] 线程已启动')
        else:
            logger.info('[定时任务] 线程已在运行，无需重复启动')
