import asyncio
import json
from functools import partial

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_current_user_sse, get_db
from app.models.modification import Modification
from app.models.message import Message
from app.models.user import User
from app.schemas.modification import ModificationCreate, ModificationOut
from app.services.generation import resolve_session
from app.services.modification import run_modification_task
from app.services.project import get_owned_project
from app.services.events import get_broker
from app.services.task_manager import get_task_manager

router = APIRouter(tags=["modifications"])


def _mod_out(modification: Modification) -> ModificationOut:
    return ModificationOut.model_validate(modification)


def _get_owned_modification(db: Session, modification_id: int, user_id: int) -> Modification:
    modification = db.get(Modification, modification_id)
    if modification is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="修改任务不存在")
    get_owned_project(db, modification.project_id, user_id)
    return modification


@router.post("/api/projects/{project_id}/modifications", response_model=ModificationOut, status_code=201)
async def create_modification(
    project_id: int,
    payload: ModificationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, project_id, user.id)
    session = resolve_session(db, project, user.id, payload.session_id)
    modification = Modification(
        project_id=project_id,
        session_id=session.id,
        generation_id=payload.generation_id,
        selector_json=payload.selector,
        element_snapshot=payload.element_snapshot,
        instruction=payload.instruction.strip(),
        related_files_json=payload.related_files,
        status="pending",
        max_attempts=2,
    )
    db.add(
        Message(
            session_id=session.id,
            role="user",
            content=payload.instruction.strip(),
            msg_type="text",
        )
    )
    db.add(modification)
    db.commit()
    db.refresh(modification)
    await get_task_manager().enqueue(partial(run_modification_task, modification.id))
    return _mod_out(modification)


@router.get("/api/modifications/{modification_id}", response_model=ModificationOut)
def get_modification(modification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _mod_out(_get_owned_modification(db, modification_id, user.id))


@router.get("/api/projects/{project_id}/modifications/active", response_model=ModificationOut | None)
def get_active_modification(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_project(db, project_id, user.id)
    modification = (
        db.query(Modification)
        .filter(Modification.project_id == project_id, Modification.status.in_(["pending", "running", "cancel_requested"]))
        .order_by(Modification.created_at.desc())
        .first()
    )
    return _mod_out(modification) if modification is not None else None


@router.post("/api/modifications/{modification_id}/cancel")
def cancel_modification(modification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    modification = _get_owned_modification(db, modification_id, user.id)
    if modification.status in {"pending", "running"}:
        modification.status = "cancel_requested"
        db.commit()
        return {"ok": True, "status": "cancelling"}
    return {"ok": True, "status": modification.status}


@router.get("/api/modifications/{modification_id}/events")
async def modification_events(
    modification_id: int,
    last_event_id: str | None = Header(default=None),
    user: User = Depends(get_current_user_sse),
    db: Session = Depends(get_db),
):
    _get_owned_modification(db, modification_id, user.id)
    broker = get_broker()
    queue = await broker.subscribe(modification_id)
    try:
        cursor = int(last_event_id or "0")
    except ValueError:
        cursor = 0
    replay = await broker.replay(modification_id, cursor) if cursor > 0 else []

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
            await broker.unsubscribe(modification_id, queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
