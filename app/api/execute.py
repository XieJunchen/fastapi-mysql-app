from fastapi import APIRouter, Depends, HTTPException, Body, File, UploadFile
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models import Workflow
import requests
import json
import os
from fastapi.responses import FileResponse
import uuid
from app.crud import create_execute_record, update_execute_record, get_execute_record
from sqlalchemy import desc
from app.tasks.polling import start_polling_if_needed
from app.utils.config import load_config

try:
    from qiniu import Auth, put_data
    QINIU_AVAILABLE = True
except ImportError:
    QINIU_AVAILABLE = False

from fastapi import Request

router = APIRouter()

# 全局加载 config，自动支持环境变量注入
config_json = load_config()

UPLOAD_TYPE = (config_json.get("upload", {}) or {}).get("type", "local")
UPLOAD_LOCAL_DIR = (config_json.get("upload", {}) or {}).get("local_dir", "./output")
QINIU = (config_json.get("upload", {}) or {}).get("qiniu", {})
QINIU_ACCESS_KEY = QINIU.get("access_key", "")
QINIU_SECRET_KEY = QINIU.get("secret_key", "")
QINIU_BUCKET_NAME = QINIU.get("bucket_name", "")
QINIU_DOMAIN = QINIU.get("domain", "")
COMFYUI_BASE_URL = (config_json.get("comfyui", {}) or {}).get("base_url", "http://127.0.0.1:8188")
RUNNINGHUB_API_URL = (config_json.get("runninghub", {}) or {}).get("api_url", "https://www.runninghub.cn/task/openapi/ai-app/run")
RUNNINGHUB_API_KEY = (config_json.get("runninghub", {}) or {}).get("api_key", "your_api_key_here")

# comfyUI 服务相关接口统一配置
COMFYUI_API_HISTORY = f"{COMFYUI_BASE_URL}/api/history?max_items=64"
COMFYUI_API_PROMPT = f"{COMFYUI_BASE_URL}/api/prompt"
COMFYUI_API_VIEW = f"{COMFYUI_BASE_URL}/api/view"
COMFYUI_API_UPLOAD_IMAGE = f"{COMFYUI_BASE_URL}/api/upload/image"
COMFYUI_API_HISTORY_SINGLE = f"{COMFYUI_BASE_URL}/history/{{prompt_id}}"

def get_user_id_from_params(db, params):
    """从参数中获取 user_id，如果未授权或未登录返回错误信息。"""
    source = params.get("source") or None
    external_user_id = params.get("external_user_id") or None
    userId = params.get("userId") or None
    if userId or (source and external_user_id):
        from app.crud.user import get_user_by_external
        db_user = get_user_by_external(db, source, external_user_id)
        if not db_user:
            return None, {"msg": "执行失败，用户未授权", "error": "用户未登录"}
        return db_user.userId, None
    else:
        return None, {"msg": "执行失败，未找到默认用户", "error": "请先创建默认用户"}

def inject_input_schema_params(prompt, params, input_schema):
    """根据 input_schema 将 params 注入到 prompt 的对应路径。"""
    try:
        schema = json.loads(input_schema) if isinstance(input_schema, str) else input_schema
        for item in schema.get("inputs", []):
            param_name = item.get("name")
            param_path = item.get("path")
            alias = item.get("alias")
            param_key = alias if alias and alias in params else param_name
            if param_key and param_path and param_key in params:
                keys = param_path.split('.')
                node = prompt
                for k in keys[:-1]:
                    node = node.get(k) if isinstance(node, dict) else None
                    if node is None:
                        break
                if node is not None and isinstance(node, dict):
                    node[keys[-1]] = params[param_key]
    except Exception as e:
        print(f"input_schema注入参数异常: {e}")
    return prompt

def build_comfyui_payload(flow_data, params, client_id):
    """构建 comfyUI API 所需的 payload。"""
    extra_data = flow_data.get("extra_data") or getattr(params, "extra_data", {})
    prompt = flow_data.get("prompt") or getattr(params, "prompt", {})
    return {
        "client_id": client_id,
        "prompt": prompt,
        "extra_data": extra_data
    }

def build_comfyui_headers():
    """构建 comfyUI API 所需的 headers。"""
    return {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "max-age=0",
        "Comfy-User": "",
        "Origin": COMFYUI_BASE_URL,
        "Referer": f"{COMFYUI_BASE_URL}/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Content-Type": "application/json"
    }

def handle_local_workflow(db, workflow_db, params, user_id):
    """处理本地类型 workflow 的执行逻辑。"""
    try:
        flow_data = json.loads(workflow_db.workflow) if workflow_db.workflow else {}
    except Exception:
        flow_data = {}
    client_id = getattr(params, "client_id", uuid.uuid4().hex)
    prompt = flow_data.get("prompt") or getattr(params, "prompt", {})
    input_schema = getattr(workflow_db, "input_schema", None)
    if input_schema:
        prompt = inject_input_schema_params(prompt, params, input_schema)
    payload = build_comfyui_payload(flow_data, params, client_id)
    headers = build_comfyui_headers()
    if not isinstance(payload["prompt"], dict):
        return {"error": "prompt must be a dict", "actual_type": str(type(payload["prompt"])), "prompt": payload["prompt"]}
    try:
        ## print(f"========>url:{COMFYUI_API_PROMPT} , params: {payload}")
        resp = requests.post(
            COMFYUI_API_PROMPT,
            json=payload,
            headers=headers if headers else None,
            timeout=300
        )
        resp.raise_for_status()
        data = resp.json()
        prompt_id = data.get("prompt_id") or data.get("promptId")
        if prompt_id:
            create_execute_record(db, workflow_db.id, prompt_id, status="pending", user_id=user_id)
        return {"msg": "调用comfyUI本地API成功", "data": data, "type": workflow_db.flowType, "prompt_id": prompt_id}
    except Exception as e:
        return {"msg": "调用comfyUI本地API异常", "error": str(e), "type": workflow_db.flowType}

def handle_runninghub_workflow(db, workflow_db):
    """处理 runningHub 类型 workflow 的执行逻辑。"""
    node_info_list = []
    if hasattr(workflow_db, "nodeInfoList") and workflow_db.nodeInfoList:
        node_info_list = workflow_db.nodeInfoList
    else:
        try:
            node_info_list = json.loads(workflow_db.workflow) if workflow_db.workflow else []
            if not isinstance(node_info_list, list):
                node_info_list = []
        except Exception:
            node_info_list = []
    payload = {
        "webappId": getattr(workflow_db, "webappId", workflow_db.id),
        "apiKey": RUNNINGHUB_API_KEY,
        "nodeInfoList": node_info_list
    }
    headers = {
        "Host": "www.runninghub.cn",
        "Content-Type": "application/json"
    }
    try:
        resp = requests.post(RUNNINGHUB_API_URL, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == 0:
            return {"msg": "调用runningHub API成功", "data": data.get("data"), "type": workflow_db.flowType}
        else:
            return {"msg": "调用runningHub API失败", "error": data.get("msg"), "type": workflow_db.flowType, "api_payload": payload}
    except Exception as e:
        return {"msg": "调用runningHub API异常", "error": str(e), "type": workflow_db.flowType, "api_payload": payload}

@router.post("/workflow/execute/{workflow_id}")
def execute_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    params: dict = Body(default={})
):
    """工作流执行主入口，自动分流到本地或 runningHub 逻辑。"""
    start_polling_if_needed()
    user_id, user_error = get_user_id_from_params(db, params)
    if user_error:
        return user_error
    ## print(f"========>params: {params}")
    workflow_db = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow_db:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if workflow_db.flowType == "local":
        return handle_local_workflow(db, workflow_db, params, user_id)
    elif workflow_db.flowType == "runningHub":
        return handle_runninghub_workflow(db, workflow_db)
    else:
        raise HTTPException(status_code=400, detail="未知的workflow类型")

@router.get("/workflow/view")
def get_comfyui_view(filename: str):
    """获取 comfyUI 生成的图片或中间结果（直接透传图片内容）"""
    # 假设 comfyUI 输出目录为 ./output，实际路径请根据 comfyUI 配置调整
    output_dir = os.path.abspath("./output")
    file_path = os.path.join(output_dir, filename)
    if not os.path.isfile(file_path):
        return {"msg": "文件不存在", "filename": filename}
    return FileResponse(file_path, media_type="image/png")

@router.get("/workflow/intermediate/{prompt_id}")
def get_comfyui_intermediate(prompt_id: str):
    """查询 comfyUI 任务中间结果（如有）"""
    try:
        resp = requests.get(COMFYUI_API_HISTORY_SINGLE.format(prompt_id=prompt_id), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # 假设中间结果在 data['outputs'] 或类似字段，具体结构需根据 comfyUI 实际返回调整
        intermediate = data.get('outputs', {}).get('intermediate', None)
        return {"msg": "查询comfyUI中间结果成功", "intermediate": intermediate, "prompt_id": prompt_id}
    except Exception as e:
        return {"msg": "查询comfyUI中间结果异常", "error": str(e), "prompt_id": prompt_id}

def parse_outputs_from_schema(outputs, output_schema):
    """严格根据 output_schema 解析 outputs，支持多图，未命中时不做兼容兜底。"""
    result = {"image_url": None}
    image_urls = []
    # 只按 output_schema 路径解析
    if output_schema and 'outputs' in output_schema:
        for item in output_schema['outputs']:
            path = item.get('path')
            name = item.get('name')
            if path and name:
                try:
                    node = outputs
                    for part in path.replace(']', '').split('.'):
                        if '[' in part:
                            k, idx = part.split('[')
                            node = node.get(k)
                            if node is not None:
                                node = node[int(idx)]
                            else:
                                node = None
                                break
                        else:
                            node = node.get(part) if isinstance(node, dict) else None
                        if node is None:
                            break
                    # 只支持 node 为图片url、图片url列表、images结构、text结构
                    if isinstance(node, str):
                        image_urls.append(node)
                    elif isinstance(node, list):
                        for n in node:
                            if isinstance(n, str):
                                image_urls.append(n)
                            elif isinstance(n, list):
                                image_urls.extend([x for x in n if isinstance(x, str)])
                            elif isinstance(n, dict) and 'filename' in n:
                                image_urls.append(f"{COMFYUI_API_VIEW}?filename={n['filename']}")
                    elif isinstance(node, dict):
                        if 'filename' in node:
                            image_urls.append(f"{COMFYUI_API_VIEW}?filename={node['filename']}")
                except Exception:
                    pass
    # 严格模式：output_schema 没命中就返回空，不再 fallback
    if image_urls:
        if len(image_urls) == 1:
            result = {"image_url": image_urls[0]}
        else:
            result = {"list_image_url": image_urls}
    else:
        result = {"image_url": None}
    return result

@router.get("/workflow/final/{prompt_id}")
def get_comfyui_final(prompt_id: str, workflow_id: int = None, db: Session = Depends(get_db)):
    """查询 comfyUI 任务最终结果，优先查本地执行记录表，未命中再查 comfyUI 并自动更新本地。返回结构始终为 {outputs: {...}}"""
    # 1. 优先查本地执行记录表
    record = get_execute_record(db, prompt_id)
    if record and record.status == "finished" and record.result:
        outputs = record.result.get("outputs") if isinstance(record.result, dict) else None
        return {"msg": "本地缓存命中", "outputs": outputs, "prompt_id": prompt_id}
    # 2. 本地未命中，查 comfyUI
    try:
        resp = requests.get(COMFYUI_API_HISTORY, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        resp_data = data.get(prompt_id, {})
        outputs = resp_data.get('outputs', {})
        messages = resp_data.get('status', {}).get('messages', [])
        workflow_id_val = workflow_id if workflow_id is not None else resp_data.get('workflow_id')
        workflow_db = db.query(Workflow).filter(Workflow.id == workflow_id_val).first() if workflow_id_val else None
        output_schema = None
        if workflow_db and getattr(workflow_db, 'output_schema', None):
            try:
                output_schema = json.loads(workflow_db.output_schema) if isinstance(workflow_db.output_schema, str) else workflow_db.output_schema
            except Exception:
                output_schema = None
        # 拆分：输出解析单独函数
        result = parse_outputs_from_schema(outputs, output_schema)
        # 自动更新本地执行记录表
        if result:
            ## print(f"========>更新执行记录 {prompt_id}，状态: finished", f"结果: {result}, messages: {messages}")
            update_execute_record(db, prompt_id, status='finished', result={"outputs": result}, messages=messages)
            return {"msg": "解析成功", "outputs": result, "prompt_id": prompt_id}
        else:
            return {"msg": "任务还在进行中，请稍后再试", "outputs": {}, "prompt_id": prompt_id}
    except Exception as e:
        update_execute_record(db, prompt_id, status="failed")
        return {"msg": "查询comfyUI最终结果异常", "error": str(e), "prompt_id": prompt_id}
