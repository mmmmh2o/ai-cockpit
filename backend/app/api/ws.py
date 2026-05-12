"""WebSocket 端点 — Phase 4 增强版 (全局事件总线)"""

import asyncio
import base64
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from app.browser.pool import browser_pool
from app.config import settings
from app.utils.event_bus import event_bus

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


@router.websocket("/ws/instances/{account_id}/chat")
async def ws_chat(websocket: WebSocket, account_id: str):
    """实时对话流 WebSocket"""
    await websocket.accept()
    logger.info(f"[WS] 对话流连接: {account_id}")

    instance = browser_pool.get(account_id)
    if not instance:
        await websocket.send_json({"type": "error", "data": {"message": "实例不存在"}})
        await websocket.close()
        return

    def sync_on_event(event_type: str, data: dict):
        asyncio.create_task(_safe_send(websocket, event_type, data))

    instance.on_event(sync_on_event)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("type") == "chat":
                    text = msg.get("message", "")
                    if text:
                        asyncio.create_task(_handle_chat(instance, text))
                elif msg.get("type") == "new_chat":
                    if instance._adapter:
                        await instance._adapter.new_conversation()
                        instance._chat_history.clear()
                        await websocket.send_json({"type": "system", "data": {"message": "新对话已创建"}})
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "data": {"message": "无效的消息格式"}})
    except WebSocketDisconnect:
        logger.info(f"[WS] 对话流断开: {account_id}")
    except Exception as e:
        logger.error(f"[WS] 对话流错误: {e}")


async def _safe_send(ws: WebSocket, event_type: str, data: dict):
    try:
        await ws.send_json({"type": event_type, "data": data})
    except Exception:
        pass


async def _handle_chat(instance, text: str):
    try:
        await instance.send_message(text)
    except Exception as e:
        logger.error(f"[{instance.account_id}] 对话失败: {e}")


@router.websocket("/ws/global")
async def ws_global(websocket: WebSocket):
    """全局状态推送 WebSocket — 使用事件总线"""
    await event_bus.connect(websocket, "global")
    logger.info("[WS] 全局状态连接")

    try:
        while True:
            # 定期推送实例状态
            states = [s.model_dump() for s in browser_pool.list_all()]
            await websocket.send_json({
                "type": "status",
                "data": {"instances": states}
            })
            await asyncio.sleep(3.0)
    except WebSocketDisconnect:
        event_bus.disconnect(websocket, "global")
        logger.info("[WS] 全局状态断开")
    except Exception as e:
        event_bus.disconnect(websocket, "global")
        logger.error(f"[WS] 全局状态错误: {e}")
