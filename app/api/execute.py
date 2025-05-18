from fastapi import APIRouter, Depends, HTTPException, Body, File, UploadFile
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models import Workflow
import requests
import json
import os
from fastapi.responses import FileResponse, StreamingResponse
import uuid

router = APIRouter()

RUNNINGHUB_API_URL = "https://www.runninghub.cn/task/openapi/ai-app/run"
RUNNINGHUB_API_KEY = "your_api_key_here"  # TODO: 替换为实际API Key，可考虑从配置或环境变量读取

# comfyUI 服务相关接口统一配置
COMFYUI_BASE_URL = "http://127.0.0.1:8188"
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
        # comfyUI 本地执行
        try:
            flow_data = json.loads(workflow_db.workflow) if workflow_db.workflow else {}
        except Exception:
            flow_data = {}
        client_id = getattr(params, "client_id", uuid.uuid4().hex)
        extra_data = flow_data.get("extra_data") or getattr(params, "extra_data", {})
        prompt = flow_data.get("prompt") or getattr(params, "prompt", {})
        # 动态替换 class_type=LoadImage 的 image 字段
        new_image = params.get("image") if isinstance(params, dict) else None
        if new_image and isinstance(prompt, dict):
            for node in prompt.values():
                if isinstance(node, dict) and node.get("class_type") == "LoadImage":
                    if "inputs" in node and isinstance(node["inputs"], dict):
                        node["inputs"]["image"] = new_image
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
        # 类型校验，防止 prompt 不是 dict
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
def get_comfyui_final(prompt_id: str):
    """查询 comfyUI 任务最终结果（如有），返回图片URL地址"""
    try:
        resp = requests.get(COMFYUI_API_HISTORY, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        resp_data = data.get(prompt_id, {})
        outputs = resp_data.get('outputs', {})
        image_info = None
        if isinstance(outputs, dict):
            for v in outputs.values():
                images = v.get('images') if isinstance(v, dict) else None
                if images and isinstance(images, list) and images and 'filename' in images[0]:
                    image_info = images[0]
                    break
        if image_info and image_info.get('filename'):
            filename = image_info['filename']
            image_url = f"{COMFYUI_API_VIEW}?filename={filename}"
            return {
                "msg": "图片已生成",
                "image_url": image_url,
                "filename": filename,
                "prompt_id": prompt_id
            }
        final = outputs.get('final', None)
        return {"msg": "未找到图片，返回final字段", "final": final, "prompt_id": prompt_id}
    except Exception as e:
        return {"msg": "查询comfyUI最终结果异常", "error": str(e), "prompt_id": prompt_id}


@router.post("/upload/image")
def upload_and_forward_image(file: UploadFile = File(...)):
    """接收图片文件，转发到 comfyUI /api/upload/image，并返回 name 字段和图片URL（可回显）"""
    try:
        # 读取上传内容
        file_bytes = file.file.read()
        files = {'image': (file.filename, file_bytes, file.content_type)}
        resp = requests.post(COMFYUI_API_UPLOAD_IMAGE, files=files, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        name = data.get("name", "")
        img_type = data.get("type", "input") or "input"
        url = f"{COMFYUI_API_VIEW}?type={img_type}&filename={name}" if name else ""
        return {
            "name": name,
            "url": url,
            "subfolder": data.get("subfolder", ""),
            "type": img_type
        }
    except Exception as e:
        return {"msg": "图片上传转发失败", "error": str(e)}
