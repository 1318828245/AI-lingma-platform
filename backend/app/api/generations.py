import asyncio
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user, get_current_user_sse, get_db
from app.models.generation import Generation
from app.models.user import User
from app.schemas.generation import (
    GenerationCreate,
    GenerationMessageIn,
    GenerationOut,
    StackAdviceIn,
    StackAdviceOut,
)
from app.services.events import get_broker
from app.services.generation import (
    create_generation,
    get_generation_for_user,
    resolve_session,
    add_message,
)
from app.services.project import get_owned_project
from app.services.route_agent import route_tech_stack
from app.services.task_manager import get_task_manager

router = APIRouter(tags=["generations"])


def _gen_out(gen: Generation) -> GenerationOut:
    return GenerationOut.model_validate(gen)


@router.post("/api/projects/{project_id}/stack-advice", response_model=StackAdviceOut)
async def get_stack_advice(
    project_id: int,
    payload: StackAdviceIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, project_id, user.id)
    return await route_tech_stack(payload.requirement.strip(), project.tech_stack)


@router.post(
    "/api/projects/{project_id}/generations",
    response_model=GenerationOut,
    status_code=201,
)
async def create_generation_endpoint(
    project_id: int,
    payload: GenerationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if len(payload.requirement) > settings.max_requirement_length:
        raise HTTPException(status_code=400, detail="需求超出长度限制")
    project = get_owned_project(db, project_id, user.id)
    session = resolve_session(db, project, user.id, payload.session_id)
    gen = create_generation(db, project, session, payload.requirement.strip())
    await get_task_manager().enqueue(
        _make_task(gen.id), on_timeout=_make_timeout(gen.id)
    )
    return _gen_out(gen)


def _make_task(generation_id: int):
    from functools import partial

    from app.services.generation import run_generation_task

    return partial(run_generation_task, generation_id)


def _make_timeout(generation_id: int):
    from functools import partial

    from app.services.generation import handle_generation_timeout

    return partial(handle_generation_timeout, generation_id)


@router.get("/api/generations/{generation_id}", response_model=GenerationOut)
def get_generation(
    generation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _gen_out(get_generation_for_user(db, generation_id, user.id))


@router.get("/api/projects/{project_id}/generations/active", response_model=GenerationOut | None)
def get_active_generation(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_project(db, project_id, user.id)
    generation = (
        db.query(Generation)
        .filter(Generation.project_id == project_id, Generation.status.in_(["pending", "running"]))
        .order_by(Generation.created_at.desc())
        .first()
    )
    return _gen_out(generation) if generation is not None else None


@router.get("/api/generations/{generation_id}/events")
async def generation_events(
    generation_id: int,
    last_event_id: str | None = Header(default=None),
    user: User = Depends(get_current_user_sse),
    db: Session = Depends(get_db),
):
    get_generation_for_user(db, generation_id, user.id)
    broker = get_broker()
    queue = await broker.subscribe(generation_id)
    try:
        cursor = int(last_event_id or "0")
    except ValueError:
        cursor = 0
    replay = await broker.replay(generation_id, cursor) if cursor > 0 else []

    async def stream():
        try:
            yield ": connected\n\n"
            for event in replay:
                yield f"id: {event.get('event_id', '')}\nevent: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue
                if event.get("type") == "closed":
                    break
                yield (
                    f"id: {event.get('event_id', '')}\n"
                    f"event: {event['type']}\n"
                    f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                )
        finally:
            await broker.unsubscribe(generation_id, queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/generations/{generation_id}/cancel")
def cancel_generation(
    generation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    gen = get_generation_for_user(db, generation_id, user.id)
    if gen.status not in (
        "pending",
        "running",
    ):
        return {"ok": True, "status": gen.status}
    gen.cancel_requested = True
    db.commit()
    return {"ok": True, "status": "cancelling"}


@router.post("/api/generations/{generation_id}/message", response_model=GenerationOut)
async def append_generation_message(
    generation_id: int,
    payload: GenerationMessageIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    gen = get_generation_for_user(db, generation_id, user.id)
    add_message(db, gen.session_id, "user", payload.message.strip(), msg_type="text")
    if gen.status == "succeeded":
        new_gen = Generation(
            project_id=gen.project_id,
            session_id=gen.session_id,
            status="pending",
            requirement=f"{gen.requirement}\n补充需求：{payload.message.strip()}",
            llm_model=gen.llm_model,
            max_build_attempts=3,
            max_eval_attempts=2,
            cancel_requested=False,
        )
        db.add(new_gen)
        db.commit()
        db.refresh(new_gen)
        await get_task_manager().enqueue(
            _make_task(new_gen.id), on_timeout=_make_timeout(new_gen.id)
        )
        return _gen_out(new_gen)
    db.commit()
    return _gen_out(gen)


@router.get("/api/generations/{generation_id}/evaluation")
def generation_evaluation(
    generation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_generation_for_user(db, generation_id, user.id)
    # M3 里程碑实现 5 维自评与评分卡片
    return {"evaluation": None, "note": "自动化评估将在 M3 里程碑实现"}
