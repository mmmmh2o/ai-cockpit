"""ChatGPT 适配器 — 完整版"""

import asyncio
from typing import Callable, Optional

from loguru import logger

from app.browser.adapters.base import BaseAdapter
from app.browser.adapters.registry import AdapterRegistry
from app.models import InstanceStatus


@AdapterRegistry.register("chatgpt")
class ChatGPTAdapter(BaseAdapter):
    """ChatGPT 网页版适配器"""

    platform_name = "chatgpt"
    platform_url = "https://chatgpt.com"

    # DOM 选择器
    selector_input = "#prompt-textarea"
    selector_input_fallback = "div[contenteditable='true']"
    selector_send_btn = 'button[data-testid="send-button"]'
    selector_response = '[data-message-author-role="assistant"]'
    selector_response_text = '.markdown'  # 回复内容的文本容器
    selector_stop_btn = 'button[aria-label="Stop generating"]'
    selector_login_form = 'button[aria-label="Log in"]'
    selector_captcha = 'iframe[src*="recaptcha"], iframe[src*="hcaptcha"]'
    selector_new_chat = 'nav a[href="/"]'
    selector_error_toast = '[data-testid="toast"]'
    selector_model_selector = 'button[data-testid="model-switcher"]'
    selector_quota_info = ''

    response_timeout = 180000  # ChatGPT 长回复可能要 3 分钟
    poll_interval = 0.5

    async def init(self) -> None:
        """打开 ChatGPT 页面"""
        await self.page.goto(self.platform_url, wait_until="domcontentloaded")
        # 等待页面加载完成
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
            # 先等页面稳定
            await self.page.wait_for_timeout(2000)

            # 有登录按钮 → 未登录
            login_btn = await self.page.query_selector(self.selector_login_form)
            if login_btn:
                logger.info(f"[{self.platform_name}] 检测到登录按钮，未登录")
                return False

            # 有输入框 → 已登录
            input_el = await self.page.query_selector(self.selector_input)
            if input_el:
                logger.info(f"[{self.platform_name}] 已登录")
                return True

            # 两者都没有 → 可能在加载中
            logger.warning(f"[{self.platform_name}] 状态不确定")
            return False
        except Exception as e:
            logger.error(f"[{self.platform_name}] 登录检测异常: {e}")
            return False

    async def send_message(self, text: str) -> None:
        """发送消息"""
        # 尝试找输入框
        input_el = await self.page.query_selector(self.selector_input)
        if not input_el:
            input_el = await self.page.query_selector(self.selector_input_fallback)
        if not input_el:
            raise RuntimeError("找不到输入框")

        # 清空并输入
        await input_el.click()
        await self.page.wait_for_timeout(200)

        # 用键盘输入（更可靠）
        await input_el.fill("")
        await input_el.type(text, delay=10)
        await self.page.wait_for_timeout(300)

        # 发送：先尝试按钮，再尝试 Enter
        send_btn = await self.page.query_selector(self.selector_send_btn)
        if send_btn and await send_btn.is_enabled():
            await send_btn.click()
        else:
            await self.page.keyboard.press("Enter")

        logger.debug(f"[{self.platform_name}] 消息已发送")

    async def collect_response(self, on_chunk: Optional[Callable] = None) -> str:
        """流式收集回复"""
        # 等待回复出现
        try:
            await self.page.wait_for_selector(
                self.selector_response, timeout=30000
            )
        except Exception:
            raise RuntimeError("等待回复超时")

        # 流式收集
        last_text = ""
        stable_count = 0
        start_time = asyncio.get_event_loop().time()

        while True:
            # 超时检查
            elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
            if elapsed > self.response_timeout:
                logger.warning(f"[{self.platform_name}] 回复超时")
                break

            # 获取最后一条回复的文本
            elements = await self.page.query_selector_all(self.selector_response)
            if not elements:
                await self.page.wait_for_timeout(int(self.poll_interval * 1000))
                continue

            last_el = elements[-1]
            # 优先获取 markdown 容器的文本
            text_el = await last_el.query_selector(self.selector_response_text)
            if text_el:
                current_text = await text_el.inner_text()
            else:
                current_text = await last_el.inner_text()

            # 流式回调
            if on_chunk and current_text != last_text:
                new_part = current_text[len(last_text):]
                if new_part:
                    on_chunk(new_part)
                last_text = current_text

            # 检查是否还在生成
            stop_btn = await self.page.query_selector(self.selector_stop_btn)
            if not stop_btn:
                # 停止按钮消失，再等一下确认
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
        await self.page.goto(self.platform_url, wait_until="domcontentloaded")
        try:
            await self.page.wait_for_selector(self.selector_input, timeout=10000)
        except Exception:
            pass

    async def check_status(self) -> InstanceStatus:
        """检查状态"""
        try:
            # 验证码
            if await self.page.query_selector(self.selector_captcha):
                return InstanceStatus.CAPTCHA

            # 错误提示
            error = await self.get_error_message()
            if error and "rate" in error.lower():
                return InstanceStatus.RATE_LIMITED

            # 登录态
            if await self.page.query_selector(self.selector_login_form):
                return InstanceStatus.LOGGED_OUT

            # 正在生成
            if await self.page.query_selector(self.selector_stop_btn):
                return InstanceStatus.BUSY

            # 在线
            if await self.page.query_selector(self.selector_input):
                return InstanceStatus.ONLINE

            return InstanceStatus.OFFLINE
        except Exception:
            return InstanceStatus.ERROR

    async def get_quota_info(self) -> dict:
        """获取额度信息"""
        # ChatGPT 网页版不直接显示额度
        return {}
