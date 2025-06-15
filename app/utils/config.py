import os
import json
import re
from dotenv import load_dotenv

ENV_VAR_PATTERN = re.compile(r'\$\{([A-Z0-9_]+)\}')

_config_cache = None  # 全局缓存

def _replace_env_vars(obj):
    if isinstance(obj, dict):
        return {k: _replace_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_replace_env_vars(i) for i in obj]
    elif isinstance(obj, str):
        def repl(match):
            var = match.group(1)
            return os.getenv(var, match.group(0))
        return ENV_VAR_PATTERN.sub(repl, obj)
    else:
        return obj

def load_config(path="config.json"):
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    load_dotenv()
    
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    config = _replace_env_vars(raw)
    _config_cache = config
    print(f"配置文件 {path} 加载成功，已替换环境变量 config:{config}")
    return config

# 用法：
# config = load_config()
# print(config["upload"]["qiniu"]["access_key"])  # 自动替换为环境变量值
