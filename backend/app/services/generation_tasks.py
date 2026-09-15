"""Persistence and state changes for decomposed generation plans."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.generation_task import GenerationTask
from app.models.generation import Generation
from app.schemas.generation_task import GenerationTaskOut


def generation_plan(db: Session, generation: Generation) -> dict:
    tasks = db.query(GenerationTask).filter_by(generation_id=generation.id).order_by(GenerationTask.sequence_no).all()
    return {
        "generation_id": generation.id,
        "status": generation.status,
        "tasks": [GenerationTaskOut.model_validate(task).model_dump(mode="json") for task in tasks],
    }


def create_generation_tasks(db: Session, generation_id: int, plan: list[dict]) -> list[GenerationTask]:
    db.query(GenerationTask).filter_by(generation_id=generation_id).delete()
    tasks = [
        GenerationTask(
            generation_id=generation_id,
            sequence_no=index,
            title=str(step.get("step") or f"任务 {index}" )[:300],
            detail=str(step.get("detail") or ""),
        )
        for index, step in enumerate(plan, start=1)
    ]
    db.add_all(tasks)
    db.flush()
    return tasks


def mark_task(db: Session, task_id: int, status: str, summary: str | None = None) -> GenerationTask | None:
    task = db.get(GenerationTask, task_id)
    if task is None:
        return None
    task.status = status
    if status == "running":
        task.started_at = datetime.now()
    if status in {"succeeded", "skipped", "failed"}:
        task.finished_at = datetime.now()
    if summary is not None:
        task.summary = summary[:2000]
    return task
