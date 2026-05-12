"""单个 Camoufox 浏览器实例封装 — Phase 2 增强版"""

import asyncio
import time
from typing import Optional, Callable

from loguru import logger

from app.browser.adapters.base import BaseAdapter
from app.browser.adapters.registry import AdapterRegistry
from app.models import InstanceStatus, InstanceState, ChatMessage
from datetime import datetime


class BrowserInstance:
    """封装一个 Camoufox 浏览器实例"""

    def __init__(self, account_id: str, platform: str, display_name: str,
                 profile_dir: str, proxy: Optional[str] = None,
                 headless: bool = False):
        self.account_id = account_id
        self.platform = platform
        self.display_name = display_name
        self.profile_dir = profile_dir
        self.proxy = proxy
        self.headless = headless

        self._browser = None
        self._context = None
        self._page = None
        self._adapter: Optional[BaseAdapter] = None
        self._status = InstanceStatus.OFFLINE
        self._start_time: float = 0
        self._last_error: Optional[str] = None
        self._screenshot_task: Optional[asyncio.Task] = None
        self._health_task: Optional[asyncio.Task] = None
        self._latest_screenshot: Optional[bytes] = None
        self._chat_history: list[ChatMessage] = []
        self._event_callbacks: list[Callable] = []

    @property
    def status(self) -> InstanceStatus:
        return self._status

    @property
    def pid(self) -> Optional[int]:
        if self._browser:
            try:
                return self._browser.process.pid
            except Exception:
                pass
        return None

    @property
    def uptime(self) -> float:
        if self._start_time and self._status != InstanceStatus.OFFLINE:
            return time.time() - self._start_time
        return 0

    @property
    def latest_screenshot(self) -> Optional[bytes]:
        return self._latest_screenshot

    @property
    def chat_history(self) -> list[ChatMessage]:
        return self._chat_history

    def on_event(self, callback: Callable):
        """注册事件回调"""
        self._event_callbacks.append(callback)

    def _emit_event(self, event_type: str, data: dict):
        """触发事件"""
        for cb in self._event_callbacks:
            try:
                cb(event_type, data)
            except Exception as e:
                logger.warning(f"事件回调异常: {e}")

    def _set_status(self, new_status: InstanceStatus, error: Optional[str] = None):
        """更新状态并触发事件"""
        old_status = self._status
        if old_status != new_status:
            self._status = new_status
            self._last_error = error
            logger.info(f"[{self.account_id}] 状态变化: {old_status.value} -> {new_status.value}")
            self._emit_event("status_change", {
                "account_id": self.account_id,
                "old_status": old_status.value,
                "new_status": new_status.value,
                "error": error,
            })

    def to_state(self) -> InstanceState:
        return InstanceState(
            account_id=self.account_id,
            platform=self.platform,
            display_name=self.display_name,
            status=self._status,
            pid=self.pid,
            uptime_seconds=self.uptime,
            last_error=self._last_error,
        )

    async def start(self):
        """启动浏览器实例"""
        try:
            self._set_status(InstanceStatus.STARTING)
            logger.info(f"[{self.account_id}] 启动浏览器...")

            # 动态导入 camoufox
            try:
                from camoufox.async_api import AsyncCamoufox
            except ImportError:
                logger.warning("camoufox 未安装，使用 Playwright 作为 fallback")
                from playwright.async_api import async_playwright
                pw = await async_playwright().start()
                launch_args = {"headless": self.headless}
                if self.proxy:
                    launch_args["proxy"] = {"server": self.proxy}
                self._browser = await pw.firefox.launch(**launch_args)
                self._context = await self._browser.new_context(
                    viewport={"width": 1280, "height": 800}
                )
                self._page = await self._context.new_page()
            else:
                camoufox_args = {
                    "headless": self.headless,
                    "user_data_dir": self.profile_dir,
                }
                if self.proxy:
                    camoufox_args["proxy"] = {"server": self.proxy}
                self._browser = await AsyncCamoufox(**camoufox_args)
                self._page = await self._browser.new_page()

            # 获取适配器
            adapter_cls = AdapterRegistry.get(self.platform)
            if not adapter_cls:
                raise ValueError(f"未注册的平台: {self.platform}")

            self._adapter = adapter_cls(self._page)
            await self._adapter.init()

            # 检查登录态
            logged_in = await self._adapter.ensure_logged_in()
            if logged_in:
                self._set_status(InstanceStatus.ONLINE)
            else:
                self._set_status(InstanceStatus.LOGGED_OUT)
                logger.info(f"[{self.account_id}] 需要登录，等待用户操作...")

            self._start_time = time.time()
            logger.info(f"[{self.account_id}] 浏览器启动成功")

            # 启动截图循环
            self._screenshot_task = asyncio.create_task(self._screenshot_loop())
            # 启动健康检查
            self._health_task = asyncio.create_task(self._health_loop())

        except Exception as e:
            self._set_status(InstanceStatus.ERROR, str(e))
            logger.error(f"[{self.account_id}] 启动失败: {e}")
            raise

    async def stop(self):
        """停止浏览器实例"""
        logger.info(f"[{self.account_id}] 停止浏览器...")

        for task in [self._screenshot_task, self._health_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        try:
            if self._browser:
                await self._browser.close()
        except Exception as e:
            logger.warning(f"[{self.account_id}] 关闭浏览器时出错: {e}")

        self._browser = None
        self._context = None
        self._page = None
        self._adapter = None
        self._set_status(InstanceStatus.OFFLINE)
        self._start_time = 0
        logger.info(f"[{self.account_id}] 浏览器已停止")

    async def wait_for_login(self, timeout: int = 300000) -> bool:
        """等待用户完成登录"""
        if not self._adapter:
            raise RuntimeError("实例未启动")

        success = await self._adapter.wait_for_login(timeout=timeout)
        if success:
            self._set_status(InstanceStatus.ONLINE)
        return success

    async def send_message(self, text: str) -> str:
        """发送消息并获取回复"""
        if not self._adapter:
            raise RuntimeError("实例未启动")

        # 记录用户消息
        self._chat_history.append(ChatMessage(role="user", content=text))
        self._emit_event("chat", {"role": "user", "content": text})

        # 流式收集回复
        chunks = []
        def on_chunk(chunk: str):
            chunks.append(chunk)
            self._emit_event("chat_chunk", {"chunk": chunk})

        try:
            response = await self._adapter.send_and_collect(text, on_chunk=on_chunk)

            # 记录助手回复
            self._chat_history.append(ChatMessage(role="assistant", content=response))
            self._emit_event("chat", {"role": "assistant", "content": response})
            return response
        except Exception as e:
            error_msg = f"消息发送失败: {e}"
            self._chat_history.append(ChatMessage(role="system", content=error_msg))
            self._emit_event("chat", {"role": "system", "content": error_msg})
            raise

    async def _screenshot_loop(self):
        """截图循环"""
        while True:
            try:
                if self._page and self._adapter:
                    self._latest_screenshot = await self._adapter.screenshot()
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"[{self.account_id}] 截图失败: {e}")
                await asyncio.sleep(2.0)

    async def _health_loop(self):
        """健康检查循环（每 15 秒）"""
        while True:
            try:
                await asyncio.sleep(15)
                if not self._adapter or not self._page:
                    break
                new_status = await self._adapter.check_status()
                if new_status != self._status:
                    self._set_status(new_status)
                    # 自动恢复逻辑
                    if new_status == InstanceStatus.LOGGED_OUT:
                        logger.warning(f"[{self.account_id}] 登录态丢失，等待重新登录...")
                    elif new_status == InstanceStatus.CAPTCHA:
                        logger.warning(f"[{self.account_id}] 触发验证码，需要人工处理")
                    elif new_status == InstanceStatus.RATE_LIMITED:
                        logger.warning(f"[{self.account_id}] 被限流，等待恢复...")
                        await asyncio.sleep(60)  # 限流后等 60 秒
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{self.account_id}] 健康检查异常: {e}")
                await asyncio.sleep(10)

    async def check_health(self) -> InstanceStatus:
        """手动触发健康检查"""
        if not self._adapter or not self._page:
            return InstanceStatus.OFFLINE
        try:
            new_status = await self._adapter.check_status()
            if new_status != self._status:
                self._set_status(new_status)
            return self._status
        except Exception as e:
            self._set_status(InstanceStatus.ERROR, str(e))
            return self._status
