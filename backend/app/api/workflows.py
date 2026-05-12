"""工作流管理 API（Phase 1 占位）"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("")
async def list_workflows():
    """工作流列表（占位）"""
    return []


@router.post("")
async def create_workflow():
    """创建工作流（占位）"""
    return {"message": "待实现"}
