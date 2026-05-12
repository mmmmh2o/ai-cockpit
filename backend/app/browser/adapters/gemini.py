"""Gemini 适配器 — 占位，DOM 选择器待确认"""

from typing import Callable, Optional

from app.browser.adapters.base import BaseAdapter
from app.browser.adapters.registry import AdapterRegistry
from app.models import InstanceStatus


@AdapterRegistry.register("gemini")
class GeminiAdapter(BaseAdapter):
    platform_name = "gemini"
    platform_url = "https://gemini.google.com"

    selector_input = ".ql-editor"
    selector_response = ".model-response-text"
    selector_stop_btn = ""
    selector_login_form = ""
    selector_captcha = ""
    selector_new_chat = ""

    async def init(self) -> None:
        await self.page.goto(self.platform_url, wait_until="domcontentloaded")

    async def ensure_logged_in(self) -> bool:
        return True  # 待实现

    async def send_message(self, text: str) -> None:
        raise NotImplementedError("Gemini 适配器待完善")

    async def collect_response(self, on_chunk: Optional[Callable] = None) -> str:
        raise NotImplementedError("Gemini 适配器待完善")

    async def new_conversation(self) -> None:
        await self.page.goto(self.platform_url, wait_until="domcontentloaded")

    async def check_status(self) -> InstanceStatus:
        return InstanceStatus.ONLINE
