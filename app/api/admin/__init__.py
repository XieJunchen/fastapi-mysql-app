from .workflow import router as workflow_router
from .user import router as user_router
from .execute_record import router as execute_record_router
from fastapi import APIRouter

router = APIRouter()
router.include_router(workflow_router)
router.include_router(user_router)
router.include_router(execute_record_router)
