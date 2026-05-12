"""全局事件总线 — 用于前端实时推送"""

import asyncio
import json
from typing import Set
from fastapi import WebSocket
from loguru import logger


class GlobalEventBus:
    """全局事件总线，管理所有 WebSocket 连接"""

    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._instance_connections: dict[str, Set[WebSocket]] = {}

    async def connect(self, ws: WebSocket, channel: str = "global"):
        await ws.accept()
        if channel == "global":
            self._connections.add(ws)
        else:
            if channel not in self._instance_connections:
                self._instance_connections[channel] = set()
            self._instance_connections[channel].add(ws)
        logger.debug(f"[EventBus] 新连接: {channel}, 总数: {len(self._connections)}")

    def disconnect(self, ws: WebSocket, channel: str = "global"):
        if channel == "global":
            self._connections.discard(ws)
        else:
            conns = self._instance_connections.get(channel)
            if conns:
                conns.discard(ws)

    async def broadcast(self, event_type: str, data: dict):
        """广播到所有全局连接"""
        msg = json.dumps({"type": event_type, "data": data})
        dead = []
        for ws in self._connections:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.discard(ws)

    async def send_to_instance(self, instance_id: str, event_type: str, data: dict):
        """发送到特定实例的连接"""
        conns = self._instance_connections.get(instance_id, set())
        msg = json.dumps({"type": event_type, "data": data})
        dead = []
        for ws in conns:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            conns.discard(ws)


# 全局单例
event_bus = GlobalEventBus()
