"""DeepSeek 适配器 — 完整版"""

import asyncio
from typing import Callable, Optional

from loguru import logger

from app.browser.adapters.base import BaseAdapter
from app.browser.adapters.registry import AdapterRegistry
from app.models import InstanceStatus


@AdapterRegistry.register("deepseek")
class DeepSeekAdapter(BaseAdapter):
    """DeepSeek 网页版适配器"""

    platform_name = "deepseek"
    platform_url = "https://chat.deepseek.com"

    # DOM 选择器（基于实际 DeepSeek 网页结构）
    selector_input = "textarea, div[contenteditable='true']"
    selector_send_btn = 'div[role="button"][aria-disabled="false"]'
    selector_response = '.ds-markdown--block, [class*="message-content"]'
    selector_response_text = '.ds-markdown--block, [class*="message-content"]'
    selector_stop_btn = 'div[class*="stop"], button[class*="stop"]'
    selector_login_form = 'button[class*="login"], a[href*="login"]'
    selector_captcha = 'iframe[src*="captcha"]'
    selector_new_chat = 'div[class*="new-chat"], a[class*="new-chat"]'
    selector_error_toast = '.ds-message, [class*="toast"]'
    selector_quota_info = ''

    response_timeout = 180000
    poll_interval = 0.5

    async def init(self) -> None:
        """打开 DeepSeek 页面"""
        await self.page.goto(self.platform_url, wait_until="domcontentloaded")
        try:
            await self.page.wait_for_selector(
                f"{self.selector_input}, {self.selector_login_form}",
                timeout=15000
            )
        except Exception:
            logger.warning(f"[{self.platform_name}] 页面加载超时，继续尝试...")

    async def ensure_logged_in(self) -> bool:
        """检查登录态"""
        try:
            await self.page.wait_for_timeout(2000)

            # 检查 URL 是否跳转到登录页
            url = self.page.url
            if "login" in url or "signin" in url:
                logger.info(f"[{self.platform_name}] 跳转到登录页")
                return False

            # 有输入框 → 已登录
            input_el = await self.page.query_selector(self.selector_input)
            if input_el:
                logger.info(f"[{self.platform_name}] 已登录")
                return True

            logger.warning(f"[{self.platform_name}] 状态不确定")
            return False
        except Exception as e:
            logger.error(f"[{self.platform_name}] 登录检测异常: {e}")
            return False

    async def send_message(self, text: str) -> None:
        """发送消息"""
        input_el = await self.page.query_selector(self.selector_input)
        if not input_el:
            raise RuntimeError("找不到输入框")

        await input_el.click()
        await self.page.wait_for_timeout(200)
        await input_el.fill("")
        await input_el.type(text, delay=10)
        await self.page.wait_for_timeout(300)

        # 发送
        send_btn = await self.page.query_selector(self.selector_send_btn)
        if send_btn:
            await send_btn.click()
        else:
            await self.page.keyboard.press("Enter")

        logger.debug(f"[{self.platform_name}] 消息已发送")

    async def collect_response(self, on_chunk: Optional[Callable] = None) -> str:
        """流式收集回复"""
        try:
            await self.page.wait_for_selector(
                self.selector_response, timeout=30000
            )
        except Exception:
            raise RuntimeError("等待回复超时")

        last_text = ""
        stable_count = 0
        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
            if elapsed > self.response_timeout:
                logger.warning(f"[{self.platform_name}] 回复超时")
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
        logger.debug(f"[{self.platform_name}] 回复完成，长度: {len(last_text)}")
        return last_text

    async def new_conversation(self) -> None:
        """新建对话"""
        await self.safe_click(self.selector_new_chat)
        await self.page.wait_for_timeout(1000)
        # 如果点击没效果，直接导航
        input_el = await self.page.query_selector(self.selector_input)
        if not input_el:
            await self.page.goto(self.platform_url, wait_until="domcontentloaded")

    async def check_status(self) -> InstanceStatus:
        """检查状态"""
        try:
            if await self.page.query_selector(self.selector_captcha):
                return InstanceStatus.CAPTCHA

            url = self.page.url
            if "login" in url or "signin" in url:
                return InstanceStatus.LOGGED_OUT

            error = await self.get_error_message()
            if error and ("rate" in error.lower() or "limit" in error.lower()):
                return InstanceStatus.RATE_LIMITED

            if await self.page.query_selector(self.selector_stop_btn):
                return InstanceStatus.BUSY

            if await self.page.query_selector(self.selector_input):
                return InstanceStatus.ONLINE

            return InstanceStatus.OFFLINE
        except Exception:
            return InstanceStatus.ERROR

    async def get_quota_info(self) -> dict:
        """DeepSeek 额度信息"""
        try:
            # DeepSeek 可能在页面某处显示剩余额度
            quota_el = await self.page.query_selector('[class*="quota"], [class*="balance"]')
            if quota_el:
                text = await quota_el.inner_text()
                return {"raw": text}
        except Exception:
            pass
        return {}
