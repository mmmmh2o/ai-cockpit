"""实例控制 API — Phase 2 增强版"""

import json
import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from loguru import logger

from app.browser.pool import browser_pool
from app.database import get_db
from app.models import ChatRequest, ChatMessage
from datetime import datetime

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


@router.post("/{account_id}/login")
async def trigger_login(account_id: str):
    """触发登录流程（等待用户手动登录）"""
    instance = browser_pool.get(account_id)
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")

    if instance.status.value != "logged_out":
        return {"message": f"当前状态 {instance.status.value}，无需登录"}

    # 异步等待登录，返回立即响应
    asyncio.create_task(_wait_login(instance))
    return {"message": "登录流程已启动，请在浏览器窗口中完成登录"}


async def _wait_login(instance):
    """后台等待登录完成"""
    try:
        success = await instance.wait_for_login(timeout=300000)
        if success:
            logger.info(f"[{instance.account_id}] 登录成功")
        else:
            logger.warning(f"[{instance.account_id}] 登录超时")
    except Exception as e:
        logger.error(f"[{instance.account_id}] 登录流程异常: {e}")


@router.post("/{account_id}/new-chat")
async def new_chat(account_id: str):
    """新建对话"""
    instance = browser_pool.get(account_id)
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    if not instance._adapter:
        raise HTTPException(status_code=400, detail="实例未启动")
    await instance._adapter.new_conversation()
    instance._chat_history.clear()
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
        return {
            "response": response,
            "history": [m.model_dump() for m in instance.chat_history[-20:]],
        }
    except Exception as e:
        logger.error(f"对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{account_id}/history")
async def get_history(account_id: str, limit: int = 50):
    """获取对话历史"""
    instance = browser_pool.get(account_id)
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    return [m.model_dump() for m in instance.chat_history[-limit:]]


@router.delete("/{account_id}/history")
async def clear_history(account_id: str):
    """清空对话历史"""
    instance = browser_pool.get(account_id)
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    instance._chat_history.clear()
    return {"message": "已清空"}


@router.post("/{account_id}/check")
async def check_health(account_id: str):
    """手动触发健康检查"""
    instance = browser_pool.get(account_id)
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    status = await instance.check_health()
    return {"status": status.value}
