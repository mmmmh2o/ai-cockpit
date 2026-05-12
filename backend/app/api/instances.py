"""实例控制 API"""

import json

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.browser.pool import browser_pool
from app.database import get_db
from app.models import ChatRequest

router = APIRouter(prefix="/api/instances", tags=["instances"])


@router.get("")
async def list_instances():
    """所有实例状态"""
    return [state.model_dump() for state in browser_pool.list_all()]


@router.get("/{account_id}")
async def get_instance(account_id: str):
    """单个实例状态"""
    instance = browser_pool.get(account_id)
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    return instance.to_state().model_dump()


@router.post("/{account_id}/start")
async def start_instance(account_id: str):
    """启动浏览器"""
    async with await get_db() as db:
        cursor = await db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="账号不存在")

    try:
        state = await browser_pool.start(
            account_id=account_id,
            platform=row["platform"],
            display_name=row["display_name"],
            profile_dir=row["profile_dir"],
            proxy=row["proxy"],
        )
        return state.model_dump()
    except Exception as e:
        logger.error(f"启动实例失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{account_id}/stop")
async def stop_instance(account_id: str):
    """停止浏览器"""
    await browser_pool.stop(account_id)
    return {"message": "已停止"}


@router.post("/{account_id}/new-chat")
async def new_chat(account_id: str):
    """新建对话"""
    instance = browser_pool.get(account_id)
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    if not instance._adapter:
        raise HTTPException(status_code=400, detail="实例未启动")
    await instance._adapter.new_conversation()
    return {"message": "新对话已创建"}


@router.post("/{account_id}/chat")
async def chat(account_id: str, req: ChatRequest):
    """发送消息并获取回复"""
    instance = browser_pool.get(account_id)
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    if not instance._adapter:
        raise HTTPException(status_code=400, detail="实例未启动")

    try:
        response = await instance.send_message(req.message)
        return {"response": response}
    except Exception as e:
        logger.error(f"对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
