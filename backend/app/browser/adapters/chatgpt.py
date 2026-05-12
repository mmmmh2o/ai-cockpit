"""ChatGPT 适配器 — 示例适配器，后续完善 DOM 选择器"""

from typing import Callable, Optional

from app.browser.adapters.base import BaseAdapter
from app.browser.adapters.registry import AdapterRegistry
from app.models import InstanceStatus


@AdapterRegistry.register("chatgpt")
class ChatGPTAdapter(BaseAdapter):
    """ChatGPT 网页版适配器"""

    platform_name = "chatgpt"
    platform_url = "https://chatgpt.com"

    selector_input = "#prompt-textarea"
    selector_response = '[data-message-author-role="assistant"]'
    selector_stop_btn = 'button[aria-label="Stop generating"]'
    selector_login_form = 'button[aria-label="Log in"]'
    selector_captcha = 'iframe[src*="recaptcha"]'
    selector_new_chat = 'nav a[href="/"]'

    async def init(self) -> None:
        await self.page.goto(self.platform_url, wait_until="domcontentloaded")

    async def ensure_logged_in(self) -> bool:
        try:
            # 检查是否有登录按钮
            login_btn = await self.page.query_selector(self.selector_login_form)
            if login_btn:
                return False
            # 检查是否有输入框（已登录的标志）
            input_el = await self.page.query_selector(self.selector_input)
            return input_el is not None
        except Exception:
            return False

    async def send_message(self, text: str) -> None:
        input_el = await self.page.wait_for_selector(self.selector_input, timeout=10000)
        await input_el.fill(text)
        await self.page.keyboard.press("Enter")

    async def collect_response(self, on_chunk: Optional[Callable] = None) -> str:
        # 等待回复出现
        await self.page.wait_for_selector(self.selector_response, timeout=60000)
        # 等待回复完成（停止按钮消失）
        try:
            await self.page.wait_for_selector(self.selector_stop_btn, state="hidden", timeout=120000)
        except Exception:
            pass
        # 获取最后一条回复
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
            if await self.page.query_selector(self.selector_captcha):
                return InstanceStatus.CAPTCHA
            if await self.page.query_selector(self.selector_login_form):
                return InstanceStatus.LOGGED_OUT
            if await self.page.query_selector(self.selector_input):
                return InstanceStatus.ONLINE
            return InstanceStatus.OFFLINE
        except Exception:
            return InstanceStatus.ERROR
