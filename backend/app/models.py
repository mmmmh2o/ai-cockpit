"""Pydantic 数据模型 — Phase 2 增强版"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── 枚举 ──────────────────────────────────────────────

class Platform(str, Enum):
    CHATGPT = "chatgpt"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"
    DOUBAO = "doubao"


class InstanceStatus(str, Enum):
    OFFLINE = "offline"
    STARTING = "starting"
    ONLINE = "online"
    LOGGED_OUT = "logged_out"
    CAPTCHA = "captcha"
    QUOTA_EXHAUSTED = "quota_exhausted"
    RATE_LIMITED = "rate_limited"
    BUSY = "busy"
    ERROR = "error"


class WorkflowMode(str, Enum):
    PIPELINE = "pipeline"
    ROUNDTABLE = "roundtable"
    REVIEW_LOOP = "review_loop"
    DEBATE = "debate"


# ── 账号 ──────────────────────────────────────────────

class AccountCreate(BaseModel):
    platform: Platform
    display_name: str
    profile_dir: Optional[str] = None
    proxy: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class Account(AccountCreate):
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ── 实例 ──────────────────────────────────────────────

class InstanceState(BaseModel):
    account_id: str
    platform: Platform
    display_name: str
    status: InstanceStatus = InstanceStatus.OFFLINE
    pid: Optional[int] = None
    uptime_seconds: float = 0
    last_error: Optional[str] = None
    screenshot_url: Optional[str] = None


# ── 对话 ──────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    history: list[ChatMessage] = Field(default_factory=list)


# ── 工作流 ────────────────────────────────────────────

class WorkflowStep(BaseModel):
    id: str
    name: str
    instance_id: str
    prompt_template: str
    timeout: int = 300
    retries: int = 0


class WorkflowCreate(BaseModel):
    name: str
    mode: WorkflowMode
    steps: list[WorkflowStep] = Field(default_factory=list)


class Workflow(WorkflowCreate):
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── WebSocket 消息 ────────────────────────────────────

class WSMessage(BaseModel):
    type: str  # "screenshot" | "status" | "chat" | "chat_chunk" | "log"
    data: dict


# ── 事件通知 ──────────────────────────────────────────

class InstanceEvent(BaseModel):
    event_type: str  # "status_change" | "chat" | "chat_chunk" | "error"
    account_id: str
    data: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)
