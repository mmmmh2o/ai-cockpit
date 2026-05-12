"""适配器基类 — 所有平台适配器的抽象接口"""

from abc import ABC, abstractmethod
from typing import Callable, Optional

from app.models import InstanceStatus


class BaseAdapter(ABC):
    """适配器基类，每个 AI 平台实现一个"""

    # 平台元信息（子类必须定义）
    platform_name: str = ""
    platform_url: str = ""

    # DOM 选择器（子类定义）
    selector_input: str = ""
    selector_response: str = ""
    selector_stop_btn: str = ""
    selector_login_form: str = ""
    selector_captcha: str = ""
    selector_new_chat: str = ""

    def __init__(self, page):
        self.page = page

    # ── 生命周期 ─────────────────────────────

    @abstractmethod
    async def init(self) -> None:
        """打开目标页面"""

    @abstractmethod
    async def ensure_logged_in(self) -> bool:
        """确认登录态"""

    # ── 核心交互 ─────────────────────────────

    @abstractmethod
    async def send_message(self, text: str) -> None:
        """发送消息"""

    @abstractmethod
    async def collect_response(self, on_chunk: Optional[Callable] = None) -> str:
        """流式收集回复"""

    @abstractmethod
    async def new_conversation(self) -> None:
        """新建对话"""

    # ── 状态检测 ─────────────────────────────

    @abstractmethod
    async def check_status(self) -> InstanceStatus:
        """返回实例状态"""

    async def get_quota_info(self) -> dict:
        """额度信息（可选实现）"""
        return {}

    # ── 截图 ─────────────────────────────────

    async def screenshot(self) -> bytes:
        """截图"""
        return await self.page.screenshot(type="jpeg", quality=60)
