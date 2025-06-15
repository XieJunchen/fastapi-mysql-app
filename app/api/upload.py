from fastapi import APIRouter, File, UploadFile
import os
import uuid
import shutil
from app.utils.config import load_config

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
try:
    from qiniu import Auth, put_data
    QINIU_AVAILABLE = True
except ImportError:
    QINIU_AVAILABLE = False

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
