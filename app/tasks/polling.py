import threading
import time
import requests
from sqlalchemy import desc
from app.db.database import SessionLocal
from app.crud.execute_record import get_execute_record_list, update_execute_record
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

# 全局定时任务控制变量
polling_thread = None
polling_thread_lock = threading.Lock()

def poll_latest_prompt_result(COMFYUI_API_HISTORY_SINGLE):
    empty_count = 0  # 连续无待处理记录的计数
    max_empty_count = 10  # 阈值，连续10次无记录则自动退出
    max_poll_count = 60  # 单个prompt最多轮询次数（如5秒一次，60次约5分钟）
    prompt_poll_count = {}  # 记录每个prompt_id的轮询次数
    from app.api.execute import COMFYUI_API_HISTORY  # 避免循环引用
    while True:
        db = SessionLocal()
        try:
            # 批量同步所有有 outputs 的历史记录到本地
            try:
                resp = requests.get(COMFYUI_API_HISTORY, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for pid, item in data.items():
                        outputs = item.get('outputs')
                        messages = item.get('status', {}).get('messages', [])
                        if outputs:
                            rec = db.query(get_execute_record_list.__globals__['ExecuteRecord']).filter_by(prompt_id=pid).first()
                            if rec and rec.status != "finished":
                                # 新增：查 workflow_id，查 workflow，取 output_schema，标准化 outputs
                                workflow_id = rec.workflow_id
                                workflow_db = db.query(get_execute_record_list.__globals__['Workflow']).filter_by(id=workflow_id).first() if workflow_id else None
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
                                update_execute_record(db, pid, status="finished", result=result_data, messages=messages)
                                logging.info(f'[批量同步] prompt_id={pid} 检测到outputs，已标准化并状态更新为finished')
            except Exception as e:
                logging.warning(f'[批量同步] comfyUI history 批量同步异常: {e}')
            logging.info('开始轮询最新的prompt结果...')
            records = db.query(get_execute_record_list.__globals__['ExecuteRecord']) \
                .filter(get_execute_record_list.__globals__['ExecuteRecord'].status.in_(['pending', 'running'])) \
                .order_by(desc(get_execute_record_list.__globals__['ExecuteRecord'].id)).limit(1).all()
            if records:
                empty_count = 0  # 有记录则重置计数
                record = records[0]
                prompt_id = record.prompt_id
                prompt_poll_count.setdefault(prompt_id, 0)
                prompt_poll_count[prompt_id] += 1
                logging.info(f'检测到待处理记录 prompt_id={prompt_id}，开始请求API')
                try:
                    url = COMFYUI_API_HISTORY_SINGLE.format(prompt_id=prompt_id)
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        data = r.json()
                        outputs = data.get("outputs")
                        if outputs:
                            messages = data.get('status', {}).get('messages', [])
                            update_execute_record(db, prompt_id, status="finished", result=data, messages=messages)
                            logging.info(f'prompt_id={prompt_id} 处理完成，状态已更新为finished')
                            prompt_poll_count.pop(prompt_id, None)
                        else:
                            # 超过最大轮询次数才判定为失败
                            if prompt_poll_count[prompt_id] >= max_poll_count:
                                messages = data.get('status', {}).get('messages', [])
                                update_execute_record(db, prompt_id, status="failed", result=data, messages=messages)
                                logging.info(f'prompt_id={prompt_id} 超过最大轮询次数未检测到outputs，状态已更新为failed')
                                prompt_poll_count.pop(prompt_id, None)
                            else:
                                logging.info(f'prompt_id={prompt_id} 未检测到outputs，继续轮询（第{prompt_poll_count[prompt_id]}次）')
                    else:
                        logging.warning(f'请求API失败，状态码: {r.status_code}, prompt_id={prompt_id}')
                except Exception as e:
                    logging.error(f"[polling] 轮询prompt_id={prompt_id}异常: {e}")
            else:
                empty_count += 1
                logging.info(f'暂无待处理的prompt记录，已连续{empty_count}次')
                if empty_count >= max_empty_count:
                    logging.info(f'连续{max_empty_count}次无待处理记录，自动退出轮询线程')
                    break
            time.sleep(5)
        finally:
            db.close()
            logging.info('数据库连接已关闭')

def start_polling_if_needed(COMFYUI_API_HISTORY_SINGLE):
    global polling_thread
    with polling_thread_lock:
        if polling_thread is None or not polling_thread.is_alive():
            logging.info('定时任务线程未启动，准备启动...')
            polling_thread = threading.Thread(target=poll_latest_prompt_result, args=(COMFYUI_API_HISTORY_SINGLE,), daemon=True)
            polling_thread.start()
            logging.info('定时任务线程已启动')
        else:
            logging.info('定时任务线程已在运行，无需重复启动')
