from fastapi import APIRouter, Depends, HTTPException, Body, File, UploadFile
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models import Workflow
import requests
import json
import os
from fastapi.responses import FileResponse, StreamingResponse
import uuid
import shutil

try:
    from qiniu import Auth, put_data
    QINIU_AVAILABLE = True
except ImportError:
    QINIU_AVAILABLE = False

from fastapi import Request

router = APIRouter()

# 读取 config.json 配置
CONFIG_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
config_json = {}
if os.path.isfile(CONFIG_JSON_PATH):
    try:
        with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
            config_json = json.load(f)
    except Exception as e:
        print(f"读取 config.json 失败: {e}")

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

@router.post("/workflow/execute/{workflow_id}")
def execute_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    params: dict = Body(default={})
):
    print(f"========>params: {params}")
    workflow_db = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow_db:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if workflow_db.flowType == "local":
        try:
            flow_data = json.loads(workflow_db.workflow) if workflow_db.workflow else {}
        except Exception:
            flow_data = {}
        client_id = getattr(params, "client_id", uuid.uuid4().hex)
        extra_data = flow_data.get("extra_data") or getattr(params, "extra_data", {})
        prompt = flow_data.get("prompt") or getattr(params, "prompt", {})
        # 动态参数注入：path 只允许从 input_schema 读取，不能从 params 读取 path 字段
        input_schema = getattr(workflow_db, "input_schema", None)
        if input_schema:
            try:
                schema = json.loads(input_schema) if isinstance(input_schema, str) else input_schema
                for item in schema.get("inputs", []):
                    param_name = item.get("name")
                    param_path = item.get("path")  # 只从 input_schema 读取
                    alias = item.get("alias")
                    # 优先用 alias 匹配 params，否则用 name
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
        payload = {
            "client_id": client_id,
            "prompt": prompt,
            "extra_data": extra_data
        }
        headers = {
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
        if not isinstance(payload["prompt"], dict):
            return {"error": "prompt must be a dict", "actual_type": str(type(payload["prompt"])), "prompt": payload["prompt"]}
        try:
            print(f"========>params: {payload}")
            resp = requests.post(
                COMFYUI_API_PROMPT,
                json=payload,
                headers=headers if headers else None,
                timeout=300
            )
            resp.raise_for_status()
            data = resp.json()
            return {"msg": "调用comfyUI本地API成功", "data": data, "type": workflow_db.flowType}
        except Exception as e:
            return {"msg": "调用comfyUI本地API异常", "error": str(e), "type": workflow_db.flowType}
    elif workflow_db.flowType == "runningHub":
        # 调用在线runningHub API
        # 1. 组装 nodeInfoList（可根据实际业务扩展，这里用 workflow.workflow 字段做演示）
        node_info_list = []
        if hasattr(workflow_db, "nodeInfoList") and workflow_db.nodeInfoList:
            node_info_list = workflow_db.nodeInfoList
        else:
            # 假设 workflow.workflow 是 json 字符串或 dict，包含节点参数
            try:
                node_info_list = json.loads(workflow_db.workflow) if workflow_db.workflow else []
                if not isinstance(node_info_list, list):
                    node_info_list = []
            except Exception:
                node_info_list = []
        payload = {
            "webappId": getattr(workflow_db, "webappId", workflow_db.id),  # 优先用 webappId 字段
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
    else:
        raise HTTPException(status_code=400, detail="未知的workflow类型")

@router.get("/workflow/history/{prompt_id}")
def get_comfyui_history(prompt_id: str):
    """查询 comfyUI 任务历史和输出结果"""
    try:
        resp = requests.get(COMFYUI_API_HISTORY_SINGLE.format(prompt_id=prompt_id), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return {"msg": "查询comfyUI任务历史成功", "data": data, "prompt_id": prompt_id}
    except Exception as e:
        return {"msg": "查询comfyUI任务历史异常", "error": str(e), "prompt_id": prompt_id}

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

@router.get("/workflow/final/{prompt_id}")
def get_comfyui_final(prompt_id: str, workflow_id: int = None, db: Session = Depends(get_db)):
    """查询 comfyUI 任务最终结果（如有），根据 output_schema 路径解析输出。支持 workflow_id 显式传参。返回结构始终为 {outputs: {...}}"""
    try:
        resp = requests.get(COMFYUI_API_HISTORY, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        resp_data = data.get(prompt_id, {})
        outputs = resp_data.get('outputs', {})
        # 优先用 workflow_id 参数，否则用 resp_data['workflow_id']
        workflow_id_val = workflow_id if workflow_id is not None else resp_data.get('workflow_id')
        workflow_db = db.query(Workflow).filter(Workflow.id == workflow_id_val).first() if workflow_id_val else None
        output_schema = None
        if workflow_db and getattr(workflow_db, 'output_schema', None):
            try:
                output_schema = json.loads(workflow_db.output_schema) if isinstance(workflow_db.output_schema, str) else workflow_db.output_schema
            except Exception:
                output_schema = None
        result = {"image_url": None}
        # 有 output_schema 时，按 path 解析
        if output_schema and 'outputs' in output_schema:
            image_urls = []
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
                        # 收集所有图片地址
                        if isinstance(node, str):
                            image_urls.append(node)
                        elif isinstance(node, list):
                            # 支持 node 为图片地址列表
                            image_urls.extend([n for n in node if isinstance(n, str)])
                    except Exception as e:
                        pass
            if image_urls:
                if len(image_urls) == 1:
                    result = {"image_url": image_urls[0]}
                else:
                    result = {"list_image_url": image_urls}
            else:
                result = {"image_url": None}
        else:
            # 没有 output_schema 时，兼容原图片逻辑，只保留 image_url/list_image_url
            image_urls = []
            if isinstance(outputs, dict):
                for v in outputs.values():
                    images = v.get('images') if isinstance(v, dict) else None
                    if images and isinstance(images, list):
                        for img in images:
                            if 'filename' in img:
                                image_urls.append(f"{COMFYUI_API_VIEW}?filename={img['filename']}")
            if image_urls:
                if len(image_urls) == 1:
                    result = {"image_url": image_urls[0]}
                else:
                    result = {"list_image_url": image_urls}
            else:
                result = {"image_url": None}
        return {"msg": "解析成功", "outputs": result, "prompt_id": prompt_id}
    except Exception as e:
        return {"msg": "查询comfyUI最终结果异常", "error": str(e), "prompt_id": prompt_id}


@router.post("/upload/image")
def upload_and_forward_image(file: UploadFile = File(...)):
    """支持本地和七牛云上传，通过 UPLOAD_TYPE 配置切换，返回图片访问地址"""
    if UPLOAD_TYPE == "qiniu":
        if not QINIU_AVAILABLE:
            return {"msg": "未安装qiniu SDK，请先 pip install qiniu"}
        if not (QINIU_ACCESS_KEY and QINIU_SECRET_KEY and QINIU_BUCKET_NAME and QINIU_DOMAIN):
            return {"msg": "七牛云配置不完整，请检查 QINIU_ACCESS_KEY、QINIU_SECRET_KEY、QINIU_BUCKET_NAME、QINIU_DOMAIN"}
        try:
            file_bytes = file.file.read()
            q = Auth(QINIU_ACCESS_KEY, QINIU_SECRET_KEY)
            key = f"input/{uuid.uuid4().hex}_{file.filename}"
            token = q.upload_token(QINIU_BUCKET_NAME, key, 3600)
            ret, info = put_data(token, key, file_bytes)
            if info.status_code == 200:
                # 判断 QINIU_DOMAIN 是否带 http/https
                domain = QINIU_DOMAIN
                if not domain.startswith("http://") and not domain.startswith("https://"):
                    domain = "http://" + domain
                url = f"{domain}/{key}"
                return {"name": url, "url": url, "type": "qiniu"}
            else:
                return {"msg": "七牛云上传失败", "error": str(info), "type": "qiniu"}
        except Exception as e:
            return {"msg": "七牛云上传异常", "error": str(e), "type": "qiniu"}
    else:
        # 本地上传
        try:
            os.makedirs(UPLOAD_LOCAL_DIR, exist_ok=True)
            filename = f"{uuid.uuid4().hex}_{file.filename}"
            file_path = os.path.join(UPLOAD_LOCAL_DIR, filename)
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            url = f"/workflow/view?filename={filename}"
            return {"name": filename, "url": url, "type": "local"}
        except Exception as e:
            return {"msg": "本地图片保存失败", "error": str(e), "type": "local"}
