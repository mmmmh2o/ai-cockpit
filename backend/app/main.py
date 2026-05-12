"""FastAPI 主入口 — Phase 5 完整版"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.api import accounts, instances, workflows, ws
from app.browser.pool import browser_pool
from app.browser.adapters.registry import AdapterRegistry, auto_discover
from app.config import settings
from app.database import init_db

# 配置 loguru
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level:7s}</level> | <cyan>{name}</cyan> - {message}")
logger.add(
    str(settings.logs_dir / "cockpit-{time:YYYY-MM-DD}.log"),
    rotation="1 day",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:7s} | {name}:{function}:{line} - {message}",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("=" * 50)
    logger.info("🚀 AI Cockpit 启动中...")
    logger.info(f"   地址: http://{settings.host}:{settings.port}")
    logger.info(f"   最大并发: {settings.max_concurrent}")
    logger.info("=" * 50)

    await init_db()
    auto_discover()
    await browser_pool.start_health_check()

    logger.info("✅ 服务就绪")
    yield

    logger.info("🛑 AI Cockpit 关闭中...")
    await browser_pool.stop_health_check()
    await browser_pool.stop_all()
    logger.info("👋 已关闭")


app = FastAPI(
    title="AI Cockpit",
    description="多平台网页 AI 协同指挥台",
    version="0.3.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(accounts.router)
app.include_router(instances.router)
app.include_router(workflows.router)
app.include_router(ws.router)


@app.get("/health")
async def health():
    """健康检查"""
    instances_list = browser_pool.list_all()
    return {
        "status": "ok",
        "instances": len(instances_list),
        "online": sum(1 for i in instances_list if i.status.value in ("online", "busy")),
        "max_concurrent": settings.max_concurrent,
        "adapters": AdapterRegistry.list_platforms(),
    }


@app.get("/api/stats")
async def stats():
    """系统统计"""
    instances_list = browser_pool.list_all()
    return {
        "instances": {
            "total": len(instances_list),
            "online": sum(1 for i in instances_list if i.status.value == "online"),
            "busy": sum(1 for i in instances_list if i.status.value == "busy"),
            "offline": sum(1 for i in instances_list if i.status.value == "offline"),
            "error": sum(1 for i in instances_list if i.status.value == "error"),
        },
        "adapters": AdapterRegistry.list_adapters(),
    }


@app.get("/api/adapters")
async def list_adapters():
    """列出所有适配器"""
    return AdapterRegistry.list_adapters()


@app.post("/api/adapters/reload")
async def reload_adapters():
    """热加载适配器"""
    AdapterRegistry.reload_all()
    return {"message": "已重载", "platforms": AdapterRegistry.list_platforms()}


# 生产环境托管前端静态文件
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
