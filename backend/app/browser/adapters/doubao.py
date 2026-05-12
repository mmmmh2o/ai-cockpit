"""豆包适配器 — 完整版"""

from typing import Callable, Optional

from loguru import logger

from app.browser.adapters.base import BaseAdapter
from app.browser.adapters.registry import AdapterRegistry
from app.models import InstanceStatus


@AdapterRegistry.register("doubao")
class DoubaoAdapter(BaseAdapter):
    """豆包网页版适配器"""

    platform_name = "doubao"
    platform_url = "https://www.doubao.com"

    # DOM 选择器
    selector_input = 'textarea, div[contenteditable="true"], [class*="input"] textarea'
    selector_send_btn = 'button[class*="send"], [class*="send-btn"]'
    selector_response = '[class*="message-content"], [class*="bot-message"], [class*="response"]'
    selector_response_text = '[class*="message-content"], [class*="bot-message"]'
    selector_stop_btn = 'button[class*="stop"], [class*="stop-btn"]'
    selector_login_form = 'button[class*="login"], [class*="login-btn"]'
    selector_captcha = ''
    selector_new_chat = 'button[class*="new-chat"], [class*="new-conversation"]'
    selector_error_toast = '[class*="toast"], [class*="error-message"]'

    response_timeout = 180000
    poll_interval = 0.5

    async def init(self) -> None:
        await self.page.goto(self.platform_url, wait_until="domcontentloaded")
        try:
            await self.page.wait_for_selector(
                f"{self.selector_input}, {self.selector_login_form}",
                timeout=15000
            )
        except Exception:
            logger.warning(f"[{self.platform_name}] 页面加载超时")

    async def ensure_logged_in(self) -> bool:
        try:
            await self.page.wait_for_timeout(2000)
            url = self.page.url
            if "login" in url or "signin" in url or "passport" in url:
                return False
            input_el = await self.page.query_selector(self.selector_input)
            return input_el is not None
        except Exception as e:
            logger.error(f"[{self.platform_name}] 登录检测异常: {e}")
            return False

    async def send_message(self, text: str) -> None:
        input_el = await self.page.query_selector(self.selector_input)
        if not input_el:
            raise RuntimeError("找不到输入框")
        await input_el.click()
        await self.page.wait_for_timeout(200)
        await input_el.fill("")
        await input_el.type(text, delay=10)
        await self.page.wait_for_timeout(300)

        send_btn = await self.page.query_selector(self.selector_send_btn)
        if send_btn:
            await send_btn.click()
        else:
            await self.page.keyboard.press("Enter")
        logger.debug(f"[{self.platform_name}] 消息已发送")

    async def collect_response(self, on_chunk: Optional[Callable] = None) -> str:
        import asyncio
        try:
            await self.page.wait_for_selector(self.selector_response, timeout=30000)
        except Exception:
            raise RuntimeError("等待回复超时")

        last_text = ""
        stable_count = 0
        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
            if elapsed > self.response_timeout:
                break

            elements = await self.page.query_selector_all(self.selector_response)
            if not elements:
                await self.page.wait_for_timeout(int(self.poll_interval * 1000))
                continue

            current_text = await elements[-1].inner_text()

            if on_chunk and current_text != last_text:
                new_part = current_text[len(last_text):]
                if new_part:
                    on_chunk(new_part)
                last_text = current_text

            stop_btn = await self.page.query_selector(self.selector_stop_btn)
            if not stop_btn:
                stable_count += 1
                if stable_count >= 3:
                    break
            else:
                stable_count = 0

            await self.page.wait_for_timeout(int(self.poll_interval * 1000))

        self._last_response_text = last_text
        return last_text

    async def new_conversation(self) -> None:
        await self.safe_click(self.selector_new_chat)
        await self.page.wait_for_timeout(1000)
        if not await self.page.query_selector(self.selector_input):
            await self.page.goto(self.platform_url, wait_until="domcontentloaded")

    async def check_status(self) -> InstanceStatus:
        try:
            url = self.page.url
            if "login" in url or "passport" in url:
                return InstanceStatus.LOGGED_OUT
            if await self.page.query_selector(self.selector_stop_btn):
                return InstanceStatus.BUSY
            if await self.page.query_selector(self.selector_input):
                return InstanceStatus.ONLINE
            return InstanceStatus.OFFLINE
        except Exception:
            return InstanceStatus.ERROR
