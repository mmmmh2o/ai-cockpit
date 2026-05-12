"""截图工具"""

import asyncio
from typing import AsyncGenerator

from loguru import logger


async def screenshot_stream(instance, fps: int = 1, quality: int = 40) -> AsyncGenerator[bytes, None]:
    """生成截图流的异步生成器"""
    interval = 1.0 / fps
    while True:
        try:
            screenshot = instance.latest_screenshot
            if screenshot:
                yield screenshot
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"截图流出错: {e}")
            await asyncio.sleep(1.0)
