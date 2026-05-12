"""适配器基类 — 所有平台适配器的抽象接口"""

from abc import ABC, abstractmethod
from typing import Callable, Optional
from loguru import logger

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
    selector_error_toast: str = ""
    selector_quota_info: str = ""

    # 配置
    response_timeout: int = 120000  # 回复超时 ms
    poll_interval: float = 0.3      # 轮询间隔 s

    def __init__(self, page):
        self.page = page
        self._last_response_text: str = ""

    # ── 生命周期 ─────────────────────────────

    @abstractmethod
    async def init(self) -> None:
        """打开目标页面"""

    @abstractmethod
    async def ensure_logged_in(self) -> bool:
        """确认登录态"""

    async def wait_for_login(self, timeout: int = 300000) -> bool:
        """等待用户完成登录（有头模式下）"""
        logger.info(f"[{self.platform_name}] 等待登录...")
        try:
            await self.page.wait_for_selector(
                self.selector_input, timeout=timeout
            )
            logger.info(f"[{self.platform_name}] 登录成功")
            return True
        except Exception:
            logger.warning(f"[{self.platform_name}] 登录超时")
            return False

    # ── 核心交互 ─────────────────────────────

    @abstractmethod
    async def send_message(self, text: str) -> None:
        """发送消息"""

    @abstractmethod
    async def collect_response(self, on_chunk: Optional[Callable] = None) -> str:
        """流式收集回复"""

    async def send_and_collect(self, text: str, on_chunk: Optional[Callable] = None) -> str:
        """发送消息并收集回复（带重试）"""
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                await self.send_message(text)
                return await self.collect_response(on_chunk=on_chunk)
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"[{self.platform_name}] 发送失败，重试 {attempt + 1}/{max_retries}: {e}")
                    await self.page.wait_for_timeout(1000)
                else:
                    raise

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

    async def check_rate_limit(self) -> bool:
        """检测是否被限流"""
        return False

    async def get_error_message(self) -> Optional[str]:
        """获取页面上的错误提示"""
        if not self.selector_error_toast:
            return None
        try:
            el = await self.page.query_selector(self.selector_error_toast)
            if el:
                return await el.inner_text()
        except Exception:
            pass
        return None

    # ── 截图 ─────────────────────────────────

    async def screenshot(self) -> bytes:
        """截图"""
        return await self.page.screenshot(type="jpeg", quality=60)

    # ── 辅助方法 ─────────────────────────────

    async def safe_click(self, selector: str, timeout: int = 5000) -> bool:
        """安全点击：存在则点击，不存在不报错"""
        try:
            el = await self.page.wait_for_selector(selector, timeout=timeout)
            if el:
                await el.click()
                return True
        except Exception:
            pass
        return False

    async def safe_fill(self, selector: str, text: str, timeout: int = 5000) -> bool:
        """安全填充：存在则填充"""
        try:
            el = await self.page.wait_for_selector(selector, timeout=timeout)
            if el:
                await el.fill(text)
                return True
        except Exception:
            pass
        return False

    async def wait_for_idle(self, timeout: int = 5000) -> bool:
        """等待页面空闲（没有正在生成的回复）"""
        try:
            if self.selector_stop_btn:
                await self.page.wait_for_selector(
                    self.selector_stop_btn, state="hidden", timeout=timeout
                )
            return True
        except Exception:
            return False
