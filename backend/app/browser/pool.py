"""浏览器实例池 — 管理所有 Camoufox 实例"""

import asyncio
from typing import Dict, Optional

from loguru import logger

from app.browser.instance import BrowserInstance
from app.config import settings
from app.models import InstanceState, InstanceStatus


class BrowserPool:
    """管理所有 Camoufox 浏览器实例"""

    def __init__(self):
        self._instances: Dict[str, BrowserInstance] = {}
        self._health_task: Optional[asyncio.Task] = None

    async def start(self, account_id: str, platform: str, display_name: str,
                    profile_dir: str, proxy: Optional[str] = None) -> InstanceState:
        """启动一个浏览器实例"""
        if account_id in self._instances:
            existing = self._instances[account_id]
            if existing.status in (InstanceStatus.ONLINE, InstanceStatus.BUSY):
                logger.warning(f"[{account_id}] 实例已在运行")
                return existing.to_state()

        # 检查并发限制
        running = sum(1 for inst in self._instances.values()
                      if inst.status not in (InstanceStatus.OFFLINE, InstanceStatus.ERROR))
        if running >= settings.max_concurrent:
            raise RuntimeError(f"已达最大并发数 {settings.max_concurrent}")

        instance = BrowserInstance(
            account_id=account_id,
            platform=platform,
            display_name=display_name,
            profile_dir=profile_dir,
            proxy=proxy,
            headless=settings.headless,
        )
        await instance.start()
        self._instances[account_id] = instance
        return instance.to_state()

    async def stop(self, account_id: str):
        """停止一个浏览器实例"""
        instance = self._instances.get(account_id)
        if instance:
            await instance.stop()

    async def stop_all(self):
        """停止所有实例"""
        tasks = [inst.stop() for inst in self._instances.values()]
        await asyncio.gather(*tasks, return_exceptions=True)
        self._instances.clear()

    def get(self, account_id: str) -> Optional[BrowserInstance]:
        """获取实例"""
        return self._instances.get(account_id)

    def list_all(self) -> list[InstanceState]:
        """列出所有实例状态"""
        return [inst.to_state() for inst in self._instances.values()]

    async def remove(self, account_id: str):
        """停止并移除实例"""
        instance = self._instances.pop(account_id, None)
        if instance:
            await instance.stop()

    # ── 健康检查 ─────────────────────────────

    async def start_health_check(self, interval: float = 30.0):
        """启动定时健康检查"""
        self._health_task = asyncio.create_task(self._health_loop(interval))

    async def stop_health_check(self):
        """停止健康检查"""
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

    async def _health_loop(self, interval: float):
        """健康检查循环"""
        while True:
            try:
                for account_id, instance in list(self._instances.items()):
                    try:
                        status = await instance.check_health()
                        if status == InstanceStatus.ERROR:
                            logger.warning(f"[{account_id}] 健康检查异常，尝试重启...")
                            try:
                                await instance.stop()
                                await instance.start()
                            except Exception as e:
                                logger.error(f"[{account_id}] 重启失败: {e}")
                    except Exception as e:
                        logger.error(f"[{account_id}] 健康检查出错: {e}")
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查循环异常: {e}")
                await asyncio.sleep(interval)


# 全局实例池
browser_pool = BrowserPool()
