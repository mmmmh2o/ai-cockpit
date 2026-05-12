"""WebSocket 端点"""

import asyncio
import base64
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from app.browser.pool import browser_pool
from app.config import settings

router = APIRouter()


@router.websocket("/ws/instances/{account_id}/screen")
async def ws_screen(websocket: WebSocket, account_id: str):
    """浏览器截图流 WebSocket"""
    await websocket.accept()
    logger.info(f"[WS] 截图流连接: {account_id}")

    try:
        while True:
            instance = browser_pool.get(account_id)
            if instance and instance.latest_screenshot:
                b64 = base64.b64encode(instance.latest_screenshot).decode()
                await websocket.send_json({
                    "type": "screenshot",
                    "data": {
                        "image": b64,
                        "format": "jpeg",
                        "status": instance.status.value,
                    }
                })
            else:
                await websocket.send_json({
                    "type": "screenshot",
                    "data": {"image": None, "status": "offline"}
                })
            await asyncio.sleep(1.0 / settings.screenshot_fps)
    except WebSocketDisconnect:
        logger.info(f"[WS] 截图流断开: {account_id}")
    except Exception as e:
        logger.error(f"[WS] 截图流错误: {e}")


@router.websocket("/ws/global")
async def ws_global(websocket: WebSocket):
    """全局状态推送 WebSocket"""
    await websocket.accept()
    logger.info("[WS] 全局状态连接")

    try:
        while True:
            states = [s.model_dump() for s in browser_pool.list_all()]
            await websocket.send_json({
                "type": "status",
                "data": {"instances": states}
            })
            await asyncio.sleep(2.0)
    except WebSocketDisconnect:
        logger.info("[WS] 全局状态断开")
    except Exception as e:
        logger.error(f"[WS] 全局状态错误: {e}")
