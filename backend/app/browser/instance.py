"""单个 Camoufox 浏览器实例封装"""

import asyncio
import time
from typing import Optional

from loguru import logger

from app.browser.adapters.base import BaseAdapter
from app.browser.adapters.registry import AdapterRegistry
from app.models import InstanceStatus, InstanceState


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
        self._latest_screenshot: Optional[bytes] = None

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
            self._status = InstanceStatus.STARTING
            logger.info(f"[{self.account_id}] 启动浏览器...")

            # 动态导入 camoufox（避免未安装时阻塞其他功能）
            try:
                from camoufox.async_api import AsyncCamoufox
            except ImportError:
                logger.error("camoufox 未安装，使用 Playwright 作为 fallback")
                from playwright.async_api import async_playwright
                pw = await async_playwright().start()
                launch_args = {
                    "headless": self.headless,
                }
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

            self._status = InstanceStatus.ONLINE
            self._start_time = time.time()
            self._last_error = None
            logger.info(f"[{self.account_id}] 浏览器启动成功")

            # 启动截图循环
            self._screenshot_task = asyncio.create_task(self._screenshot_loop())

        except Exception as e:
            self._status = InstanceStatus.ERROR
            self._last_error = str(e)
            logger.error(f"[{self.account_id}] 启动失败: {e}")
            raise

    async def stop(self):
        """停止浏览器实例"""
        logger.info(f"[{self.account_id}] 停止浏览器...")
        if self._screenshot_task:
            self._screenshot_task.cancel()
            try:
                await self._screenshot_task
            except asyncio.CancelledError:
                pass

        try:
            if self._browser:
                # Playwright browser or Camoufox both have .close()
                await self._browser.close()
        except Exception as e:
            logger.warning(f"[{self.account_id}] 关闭浏览器时出错: {e}")

        self._browser = None
        self._context = None
        self._page = None
        self._adapter = None
        self._status = InstanceStatus.OFFLINE
        self._start_time = 0
        logger.info(f"[{self.account_id}] 浏览器已停止")

    async def _screenshot_loop(self):
        """截图循环 — 每秒截一帧"""
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

    async def send_message(self, text: str) -> str:
        """发送消息并获取回复"""
        if not self._adapter:
            raise RuntimeError("实例未启动")
        await self._adapter.send_message(text)
        return await self._adapter.collect_response()

    async def check_health(self) -> InstanceStatus:
        """健康检查"""
        if not self._adapter or not self._page:
            return InstanceStatus.OFFLINE
        try:
            new_status = await self._adapter.check_status()
            if new_status != self._status:
                logger.info(f"[{self.account_id}] 状态变化: {self._status} -> {new_status}")
                self._status = new_status
            return self._status
        except Exception as e:
            self._status = InstanceStatus.ERROR
            self._last_error = str(e)
            return self._status
