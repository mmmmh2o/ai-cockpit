"""消息总线 — AI 间通信的核心枢纽"""

import asyncio
import uuid
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

from loguru import logger
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    PROMPT = "prompt"        # 用户/上游发来的指令
    RESPONSE = "response"    # AI 的回复
    SYSTEM = "system"        # 系统注入的上下文
    CONTROL = "control"      # 控制信号（暂停/继续/终止）


class BusMessage(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    workflow_run_id: str = ""
    step_id: str = ""
    source_id: str = ""      # 发送者 instance_id
    target_id: str = ""      # 接收者 instance_id（空 = 广播）
    msg_type: MessageType = MessageType.PROMPT
    content: str = ""
    metadata: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# 类型别名
MessageHandler = Callable[[BusMessage], None]


class MessageBus:
    """
    所有 AI 间交互的中枢
    - 中间件机制：日志、过滤、注入
    - 全量消息历史记录
    - 按工作流过滤消息
    """

    def __init__(self):
        self._handlers: dict[str, list[MessageHandler]] = defaultdict(list)
        self._history: list[BusMessage] = []
        self._middleware: list[Callable] = []
        self._lock = asyncio.Lock()

    def register(self, instance_id: str, handler: MessageHandler):
        """注册消息处理器"""
        self._handlers[instance_id].append(handler)
        logger.debug(f"[Bus] 注册处理器: {instance_id}")

    def unregister(self, instance_id: str):
        """注销消息处理器"""
        self._handlers.pop(instance_id, None)
        logger.debug(f"[Bus] 注销处理器: {instance_id}")

    def use(self, middleware: Callable):
        """添加中间件"""
        self._middleware.append(middleware)

    async def send(self, msg: BusMessage):
        """发送消息（经过中间件处理）"""
        # 中间件处理
        for mw in self._middleware:
            try:
                msg = await mw(msg) if asyncio.iscoroutinefunction(mw) else mw(msg)
                if msg is None:
                    return  # 中间件拦截
            except Exception as e:
                logger.error(f"[Bus] 中间件异常: {e}")

        async with self._lock:
            self._history.append(msg)

        # 路由消息
        if msg.target_id:
            # 定向发送
            handlers = self._handlers.get(msg.target_id, [])
            for handler in handlers:
                try:
                    result = handler(msg)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"[Bus] 处理器异常 ({msg.target_id}): {e}")
        else:
            # 广播（发送给除 source 外的所有）
            for iid, handlers in self._handlers.items():
                if iid == msg.source_id:
                    continue
                for handler in handlers:
                    try:
                        result = handler(msg)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        logger.error(f"[Bus] 处理器异常 ({iid}): {e}")

        logger.debug(f"[Bus] 消息 {msg.id}: {msg.source_id} -> {msg.target_id or '*'} [{msg.msg_type.value}]")

    def get_history(self, workflow_run_id: Optional[str] = None,
                    step_id: Optional[str] = None,
                    limit: int = 100) -> list[BusMessage]:
        """获取消息历史"""
        msgs = self._history
        if workflow_run_id:
            msgs = [m for m in msgs if m.workflow_run_id == workflow_run_id]
        if step_id:
            msgs = [m for m in msgs if m.step_id == step_id]
        return msgs[-limit:]

    def clear_history(self, workflow_run_id: Optional[str] = None):
        """清空历史"""
        if workflow_run_id:
            self._history = [m for m in self._history if m.workflow_run_id != workflow_run_id]
        else:
            self._history.clear()


# 全局消息总线
message_bus = MessageBus()


# ── 中间件示例 ──────────────────────────────────────

async def logging_middleware(msg: BusMessage) -> BusMessage:
    """日志中间件"""
    logger.info(f"[Bus:Log] {msg.source_id} -> {msg.target_id or '*'}: {msg.content[:80]}...")
    return msg


async def inject_context_middleware(msg: BusMessage) -> BusMessage:
    """注入上下文中间件 — 在消息前注入工作流上下文"""
    # 可以在这里注入额外的上下文信息
    return msg
