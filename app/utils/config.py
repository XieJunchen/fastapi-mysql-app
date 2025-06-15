import os
import json
import re

ENV_VAR_PATTERN = re.compile(r'\$\{([A-Z0-9_]+)\}')

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
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return _replace_env_vars(raw)

# 用法：
# config = load_config()
# print(config["upload"]["qiniu"]["access_key"])  # 自动替换为环境变量值
