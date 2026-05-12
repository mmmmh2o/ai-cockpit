"""适配器注册表 — 支持运行时动态注册新平台"""

from typing import Dict, Type
from loguru import logger

from app.browser.adapters.base import BaseAdapter


class AdapterRegistry:
    """平台适配器注册表"""

    _adapters: Dict[str, Type[BaseAdapter]] = {}

    @classmethod
    def register(cls, platform_name: str):
        """装饰器：注册一个适配器"""
        def decorator(adapter_cls: Type[BaseAdapter]):
            cls._adapters[platform_name] = adapter_cls
            logger.info(f"注册适配器: {platform_name} -> {adapter_cls.__name__}")
            return adapter_cls
        return decorator

    @classmethod
    def get(cls, platform_name: str) -> Type[BaseAdapter] | None:
        """获取适配器类"""
        return cls._adapters.get(platform_name)

    @classmethod
    def list_platforms(cls) -> list[str]:
        """列出所有已注册平台"""
        return list(cls._adapters.keys())
