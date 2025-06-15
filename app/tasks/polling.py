import threading
import time
import requests
from sqlalchemy import desc
from app.db.database import SessionLocal
from app.crud.execute_record import get_execute_record_list, update_execute_record
from app.models.workflow import Workflow
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

# 全局定时任务控制变量
polling_thread = None
polling_thread_lock = threading.Lock()

def get_comfyui_history(COMFYUI_API_HISTORY):
    try:
        resp = requests.get(COMFYUI_API_HISTORY, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            logging.warning(f'[定时任务] 请求API失败，状态码: {resp.status_code}')
            return None
    except Exception as e:
        logging.error(f"[定时任务] comfyUI history 批量同步异常: {e}")
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
                workflow_db = db.query(Workflow).filter_by(id=workflow_id).first() if workflow_id else None
                output_schema = None
                if workflow_db and getattr(workflow_db, 'output_schema', None):
                    try:
                        import json
                        output_schema = json.loads(workflow_db.output_schema) if isinstance(workflow_db.output_schema, str) else workflow_db.output_schema
                    except Exception:
                        output_schema = None
                # 导入 parse_outputs_from_schema
                from app.api.execute import parse_outputs_from_schema
                std_outputs = parse_outputs_from_schema(outputs, output_schema)
                # 存储标准化 outputs 到 result["outputs"]
                result_data = dict(item)
                result_data["outputs"] = std_outputs
                update_list.append((pid, result_data, messages))
    # 批量更新
    for pid, result_data, messages in update_list:
        update_execute_record(db, pid, status="finished", result=result_data, messages=messages)
    if update_list:
        db.commit()
        logging.info(f"[定时任务] 本次批量同步 {len(update_list)} 条prompt记录")

def poll_latest_prompt_result(COMFYUI_API_HISTORY_SINGLE):
    empty_count = 0  # 连续无待处理记录的计数
    max_empty_count = 10  # 阈值，连续10次无记录则自动退出
    max_poll_count = 60  # 单个prompt最多轮询次数（如5秒一次，60次约5分钟）
    prompt_poll_count = {}  # 记录每个prompt_id的轮询次数
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
                logging.info(f'[定时任务] 暂无待处理的prompt记录，已连续{empty_count}次')
                if empty_count >= max_empty_count:
                    logging.info(f'[定时任务] 连续{max_empty_count}次无待处理记录，自动退出轮询线程')
                    break
            time.sleep(5)
    finally:
        db.close()
        logging.info('[定时任务] 数据库连接已关闭')

def start_polling_if_needed(COMFYUI_API_HISTORY_SINGLE):
    global polling_thread
    with polling_thread_lock:
        if polling_thread is None or not polling_thread.is_alive():
            logging.info('[定时任务] 线程未启动，准备启动...')
            polling_thread = threading.Thread(target=poll_latest_prompt_result, args=(COMFYUI_API_HISTORY_SINGLE,), daemon=True)
            polling_thread.start()
            logging.info('[定时任务] 线程已启动')
        else:
            logging.info('[定时任务] 线程已在运行，无需重复启动')
