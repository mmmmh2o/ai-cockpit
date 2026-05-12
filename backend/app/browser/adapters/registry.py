"""适配器注册表 — 支持运行时动态注册 & 热加载"""

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Dict, Type

from loguru import logger

from app.browser.adapters.base import BaseAdapter


class AdapterRegistry:
    """平台适配器注册表 — 支持热加载"""

    _adapters: Dict[str, Type[BaseAdapter]] = {}
    _adapter_dir: Path = Path(__file__).parent

    @classmethod
    def register(cls, platform_name: str):
        """装饰器：注册一个适配器"""
        def decorator(adapter_cls: Type[BaseAdapter]):
            cls._adapters[platform_name] = adapter_cls
            adapter_cls.platform_name = platform_name
            logger.info(f"[Registry] 注册适配器: {platform_name} -> {adapter_cls.__name__}")
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

    @classmethod
    def list_adapters(cls) -> list[dict]:
        """列出所有适配器详情"""
        return [
            {
                "platform": name,
                "class": adapter.__name__,
                "url": getattr(adapter, "platform_url", ""),
            }
            for name, adapter in cls._adapters.items()
        ]

    @classmethod
    def reload_all(cls):
        """热加载所有适配器"""
        cls._adapters.clear()
        cls._discover_adapters()
        logger.info(f"[Registry] 热加载完成，共 {len(cls._adapters)} 个适配器")

    @classmethod
    def _discover_adapters(cls):
        """自动发现并加载 adapters 目录下的所有适配器"""
        for _, module_name, _ in pkgutil.iter_modules([str(cls._adapter_dir)]):
            if module_name.startswith("_") or module_name in ("base", "registry"):
                continue
            try:
                module = importlib.import_module(f"app.browser.adapters.{module_name}")
                # 查找所有继承 BaseAdapter 的类
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseAdapter) and obj is not BaseAdapter
                            and hasattr(obj, "platform_name") and obj.platform_name):
                        if obj.platform_name not in cls._adapters:
                            cls._adapters[obj.platform_name] = obj
                            logger.info(f"[Registry] 自动发现: {obj.platform_name} -> {name}")
            except Exception as e:
                logger.error(f"[Registry] 加载模块 {module_name} 失败: {e}")

    @classmethod
    async def load_from_file(cls, file_path: str):
        """从文件热加载适配器"""
        try:
            spec = importlib.util.spec_from_file_location("dynamic_adapter", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            loaded = 0
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, BaseAdapter) and obj is not BaseAdapter
                        and hasattr(obj, "platform_name") and obj.platform_name):
                    cls._adapters[obj.platform_name] = obj
                    loaded += 1
                    logger.info(f"[Registry] 热加载: {obj.platform_name} -> {name}")

            return loaded
        except Exception as e:
            logger.error(f"[Registry] 热加载文件失败 {file_path}: {e}")
            return 0


def auto_discover():
    """启动时自动发现所有适配器"""
    AdapterRegistry._discover_adapters()
    logger.info(f"[Registry] 已注册适配器: {AdapterRegistry.list_platforms()}")
