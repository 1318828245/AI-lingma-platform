from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import init_db
from app.services.generation import recover_interrupted_tasks
from app.services.project import migrate_workspace_layout
from app.services.task_manager import get_task_manager
from app.services.task_manager import get_asset_task_manager
from app.services.assets import pending_asset_job_ids, run_asset_job
from app.services.settings_store import settings_store
from app.services.graph_checkpoint import start_graph_checkpointing, stop_graph_checkpointing
from functools import partial


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings_store.apply(get_settings(), {
        "register_enabled", "default_user_quota", "build_mode", "command_mode",
        "generation_concurrency", "modification_concurrency", "task_timeout_seconds",
        "max_requirement_length", "agent_max_iterations", "agent_max_model_steps", "agent_max_tool_calls", "agent_soft_limit_ratio", "agent_max_no_progress_steps", "llm_model", "llm_base_url", "llm_reasoning_effort",
        "llm_thinking_enabled", "eval_vision_provider", "eval_vision_model",
        "eval_vision_base_url", "eval_vision_thinking_enabled",
    })
    migrated = migrate_workspace_layout()
    if migrated:
        print(f"[startup] Migrated {migrated} workspaces to canonical ASCII names")
    recovered = recover_interrupted_tasks()
    if recovered:
        print(f"[startup] 将 {recovered} 个遗留生成任务标记为 interrupted")
    await start_graph_checkpointing()
    await get_task_manager().start()
    asset_manager = get_asset_task_manager()
    await asset_manager.start()
    for job_id in pending_asset_job_ids():
        await asset_manager.enqueue(partial(run_asset_job, job_id))
    yield
    await asset_manager.stop()
    await get_task_manager().stop()
    await stop_graph_checkpointing()


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
