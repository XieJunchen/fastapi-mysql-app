from app.db.database import get_db
from app.models import Workflow
import json

def is_url(s):
    return isinstance(s, str) and (s.startswith('http://') or s.startswith('https://'))

def fix_pictures():
    db = next(get_db())
    workflows = db.query(Workflow).all()
    for w in workflows:
        pics = w.pictures
        # 1. 字符串转list
        if isinstance(pics, str):
            try:
                pics = json.loads(pics)
            except Exception:
                pics = [p.strip() for p in pics.split(",") if p.strip()]
        # 2. 合并被错误分割的url
        if isinstance(pics, list):
            new_pics = []
            temp = ""
            for p in pics:
                if is_url(p):
                    if temp:
                        new_pics.append(temp)
                        temp = ""
                    temp = p
                else:
                    if temp:
                        if not temp.endswith(","):
                            temp += ","
                        temp += p
                    else:
                        temp = p
            if temp:
                new_pics.append(temp)
            # 再过滤一遍
            new_pics = [p for p in new_pics if is_url(p)]
            w.pictures = new_pics
            print(f"fix id={w.id} -> {w.pictures}")
    db.commit()

if __name__ == "__main__":
    fix_pictures()
