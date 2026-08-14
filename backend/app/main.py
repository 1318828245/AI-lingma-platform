from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import init_db
from app.services.generation import recover_interrupted_tasks
from app.services.task_manager import get_task_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    recovered = recover_interrupted_tasks()
    if recovered:
        print(f"[startup] 将 {recovered} 个遗留生成任务标记为 interrupted")
    await get_task_manager().start()
    yield
    await get_task_manager().stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
