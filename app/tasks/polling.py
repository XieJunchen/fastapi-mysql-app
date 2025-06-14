import threading
import time
import requests
from sqlalchemy import desc
from app.db.database import SessionLocal
from app.crud.execute_record import get_execute_record_list, update_execute_record

# 全局定时任务控制变量
polling_thread = None
polling_thread_lock = threading.Lock()

def poll_latest_prompt_result(COMFYUI_API_HISTORY_SINGLE):
    while True:
        db = SessionLocal()
        try:
            records = db.query(get_execute_record_list.__globals__['ExecuteRecord']) \
                .filter(get_execute_record_list.__globals__['ExecuteRecord'].status.in_(['pending', 'running'])) \
                .order_by(desc(get_execute_record_list.__globals__['ExecuteRecord'].id)).limit(1).all()
            if records:
                record = records[0]
                prompt_id = record.prompt_id
                try:
                    url = COMFYUI_API_HISTORY_SINGLE.format(prompt_id=prompt_id)
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        data = r.json()
                        if data and (data.get("outputs") or data.get("outputs", None) is not None):
                            messages = data.get('status', {}).get('messages', [])
                            update_execute_record(db, prompt_id, status="finished", result=data, messages=messages)
                except Exception as e:
                    print(f"[polling] 轮询prompt_id={prompt_id}异常: {e}")
            time.sleep(5)
        finally:
            db.close()

def start_polling_if_needed(COMFYUI_API_HISTORY_SINGLE):
    global polling_thread
    with polling_thread_lock:
        if polling_thread is None or not polling_thread.is_alive():
            polling_thread = threading.Thread(target=poll_latest_prompt_result, args=(COMFYUI_API_HISTORY_SINGLE,), daemon=True)
            polling_thread.start()
