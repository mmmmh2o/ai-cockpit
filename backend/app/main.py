"""FastAPI 主入口"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.api import accounts, instances, workflows, ws
from app.browser.pool import browser_pool
from app.config import settings
from app.database import init_db

# 导入适配器（触发注册）
import app.browser.adapters.chatgpt  # noqa: F401
import app.browser.adapters.deepseek  # noqa: F401
import app.browser.adapters.gemini  # noqa: F401
import app.browser.adapters.doubao  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 AI Cockpit 启动中...")
    await init_db()
    await browser_pool.start_health_check()
    logger.info(f"✅ 服务就绪: http://{settings.host}:{settings.port}")
    yield
    logger.info("🛑 AI Cockpit 关闭中...")
    await browser_pool.stop_health_check()
    await browser_pool.stop_all()
    logger.info("👋 已关闭")


app = FastAPI(
    title="AI Cockpit",
    description="多平台网页 AI 协同指挥台",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
    return {
        "status": "ok",
        "instances": len(browser_pool.list_all()),
        "max_concurrent": settings.max_concurrent,
    }


# 生产环境托管前端静态文件
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
