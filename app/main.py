from fastapi import FastAPI
from app.api import router as api_router
from app.db.database import engine, SessionLocal
from app.models import Base, Workflow
import datetime

app = FastAPI()

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    # 初始化数据
    db = SessionLocal()
    if db.query(Workflow).count() == 0:
        db.add_all([
            Workflow(name="一键移除背景", desc='模型简介\n 本模型专注于卡通机器人形象生成，擅长将卡通元素与机械设计巧妙融合，打造风格独特、色彩丰富且富有创意的机器人形象。其优势在于精准呈现未来感与趣味性，广泛适用于玩具设计、动画制作、游戏美术、文创周边等领域，为用户提供多样化、高辨识度的视觉方案，满足从儿童向到科技感的多元设计需求。',useTimes=5000, workflow="", createdTime=datetime.datetime(2025, 5, 16), picture="https://liblibai-online.liblib.cloud/img/7a5d9baa4b8d4b8caabc7cab845730f8/8c8d81f3ad6d3248efe30c2ea878d6b1b5f353a09914f591c84792a478fbb17d.png?x-oss-process=image/resize,w_764,m_lfit/format,webp", bigPicture="https://fc1tn.baidu.com/it/u=3618773086,3005188026&fm=202&src=1024&fc_m=pc_3_2&mola=new&crop=v1", pictures=["https://liblibai-online.liblib.cloud/img/7a5d9baa4b8d4b8caabc7cab845730f8/8c8d81f3ad6d3248efe30c2ea878d6b1b5f353a09914f591c84792a478fbb17d.png?x-oss-process=image/resize,w_764,m_lfit/format,webp","https://fc1tn.baidu.com/it/u=3618773086,3005188026&fm=202&src=1024&fc_m=pc_3_2&mola=new&crop=v1"],flowType="local"),
            Workflow(name="图片首尾帧串联", desc='测试测试', useTimes=2, workflow="", createdTime=datetime.datetime(2025, 5, 16), picture="https://liblibai-online.liblib.cloud/img/7a5d9baa4b8d4b8caabc7cab845730f8/edd51175658912503ca5b5218dccfd0a9ca72ef76ca4869759705a3b1e8c2998.gif", bigPicture="https://fc1tn.baidu.com/it/u=3618773086,3005188026&fm=202&src=1024&fc_m=pc_3_2&mola=new&crop=v1",flowType="local"),
            Workflow(name="图片生成视频", desc='测试测试', useTimes=0, workflow="", createdTime=datetime.datetime(2025, 5, 16), picture="https://liblibai-online.liblib.cloud/img/7a5d9baa4b8d4b8caabc7cab845730f8/dcb23100afbd752d7adbbfcc37504a56b7fef7d05c235275f86f878a1bc36f94.gif", bigPicture="https://fc1tn.baidu.com/it/u=3618773086,3005188026&fm=202&src=1024&fc_m=pc_3_2&mola=new&crop=v1",flowType="local"),
            Workflow(name="流程d", desc='测试测试', useTimes=0, workflow="", createdTime=datetime.datetime(2025, 5, 16), picture="https://pic4.zhimg.com/v2-684a0452b1442d48ed3b18dca7a4a2a8_720w.webp?source=d6434cab", bigPicture="https://fc1tn.baidu.com/it/u=3618773086,3005188026&fm=202&src=1024&fc_m=pc_3_2&mola=new&crop=v1",flowType="local"),
            Workflow(name="流程e", desc='测试测试', useTimes=0, workflow="", createdTime=datetime.datetime(2025, 5, 16), picture="https://pic4.zhimg.com/v2-684a0452b1442d48ed3b18dca7a4a2a8_720w.webp?source=d6434cab", bigPicture="https://fc1tn.baidu.com/it/u=3618773086,3005188026&fm=202&src=1024&fc_m=pc_3_2&mola=new&crop=v1",flowType="local"),
            Workflow(name="流程f", desc='测试测试', useTimes=0, workflow="", createdTime=datetime.datetime(2025, 5, 16), picture="https://pic4.zhimg.com/v2-684a0452b1442d48ed3b18dca7a4a2a8_720w.webp?source=d6434cab", bigPicture="https://fc1tn.baidu.com/it/u=3618773086,3005188026&fm=202&src=1024&fc_m=pc_3_2&mola=new&crop=v1",flowType="local"),
        ])
        db.commit()
    db.close()
    

app.include_router(api_router)