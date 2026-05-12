"""DeepSeek 适配器 — 占位，DOM 选择器待确认"""

from typing import Callable, Optional

from app.browser.adapters.base import BaseAdapter
from app.browser.adapters.registry import AdapterRegistry
from app.models import InstanceStatus


@AdapterRegistry.register("deepseek")
class DeepSeekAdapter(BaseAdapter):
    """DeepSeek 网页版适配器"""

    platform_name = "deepseek"
    platform_url = "https://chat.deepseek.com"

    selector_input = "textarea#chat-input"
    selector_response = ".ds-markdown"
    selector_stop_btn = ".ds-icon-button.stop"
    selector_login_form = ".ds-login"
    selector_captcha = ""
    selector_new_chat = ".ds-sidebar-new-chat"

    async def init(self) -> None:
        await self.page.goto(self.platform_url, wait_until="domcontentloaded")

    async def ensure_logged_in(self) -> bool:
        try:
            login_el = await self.page.query_selector(self.selector_login_form)
            if login_el:
                return False
            input_el = await self.page.query_selector(self.selector_input)
            return input_el is not None
        except Exception:
            return False

    async def send_message(self, text: str) -> None:
        input_el = await self.page.wait_for_selector(self.selector_input, timeout=10000)
        await input_el.fill(text)
        await self.page.keyboard.press("Enter")

    async def collect_response(self, on_chunk: Optional[Callable] = None) -> str:
        await self.page.wait_for_selector(self.selector_response, timeout=60000)
        try:
            await self.page.wait_for_selector(self.selector_stop_btn, state="hidden", timeout=120000)
        except Exception:
            pass
        elements = await self.page.query_selector_all(self.selector_response)
        if not elements:
            return ""
        last = elements[-1]
        text = await last.inner_text()
        if on_chunk:
            on_chunk(text)
        return text

    async def new_conversation(self) -> None:
        await self.page.goto(self.platform_url, wait_until="domcontentloaded")

    async def check_status(self) -> InstanceStatus:
        try:
            if await self.page.query_selector(self.selector_login_form):
                return InstanceStatus.LOGGED_OUT
            if await self.page.query_selector(self.selector_input):
                return InstanceStatus.ONLINE
            return InstanceStatus.OFFLINE
        except Exception:
            return InstanceStatus.ERROR
