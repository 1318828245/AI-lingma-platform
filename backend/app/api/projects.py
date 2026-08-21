from fastapi import APIRouter, Body, Depends, HTTPException, Query
from functools import partial
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.project import Project
from app.models.file import File
from app.models.generation import Generation
from app.models.modification import Modification
from app.models.template import Template
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.project import create_project, delete_project, get_owned_project, project_workspace
from app.services.assets import asset_job_wire, list_asset_jobs, list_project_assets, run_asset_job, select_asset_candidate
from app.models.asset import AssetJob
from app.services.evaluation import apply_visual_evaluation, evaluate_delivery, evaluation_wire, latest_project_evaluation
from app.services.task_manager import get_asset_task_manager

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(
    status: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Project).filter(Project.owner_id == user.id)
    if status:
        query = query.filter(Project.status == status)
    return query.order_by(Project.updated_at.desc()).all()


@router.post("", response_model=ProjectOut, status_code=201)
def create_project_endpoint(
    payload: ProjectCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template: Template | None = None
    if payload.template and payload.template != "blank":
        template = (
            db.query(Template)
            .filter(
                Template.name == payload.template,
                Template.is_active.is_(True),
            )
            .first()
        )
        if template is None:
            raise HTTPException(status_code=400, detail=f"模板不存在或已停用: {payload.template}")
    project = create_project(db, user.id, payload, template)
    return ProjectOut.model_validate(project)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProjectOut.model_validate(get_owned_project(db, project_id, user.id))


@router.get("/{project_id}/assets")
def list_assets(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_project(db, project_id, user.id)
    return {"assets": list_project_assets(db, project_id)}


@router.get("/{project_id}/evaluation")
def project_evaluation(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_project(db, project_id, user.id)
    row = latest_project_evaluation(db, project_id)
    return {"evaluation": evaluation_wire(row) if row else None}


@router.post("/{project_id}/evaluation/refresh")
async def refresh_project_evaluation(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, project_id, user.id)
    previous = latest_project_evaluation(db, project_id)
    if previous is None:
        raise HTTPException(status_code=409, detail="请先完成一次生成或修改后再检查质量")
    if previous.ref_type == "generation":
        source = db.get(Generation, previous.ref_id)
        requirement = source.requirement if source else ""
        changed_files = None
    elif previous.ref_type == "modification":
        source = db.get(Modification, previous.ref_id)
        requirement = source.instruction if source else ""
        changed_files = list(source.related_files_json or []) if source else None
    else:
        raise HTTPException(status_code=409, detail="该历史记录无法重新评估")
    if source is None:
        raise HTTPException(status_code=404, detail="原始交付记录不存在")
    row = evaluate_delivery(
        db, project_id=project_id, ref_type=previous.ref_type, ref_id=previous.ref_id,
        succeeded=True, requirement=requirement, workspace=project_workspace(project), changed_files=changed_files,
    )
    row = await apply_visual_evaluation(
        db, row, user_id=user.id, requirement=requirement, workspace=project_workspace(project),
    )
    db.commit()
    return {"evaluation": evaluation_wire(row)}


@router.get("/{project_id}/asset-jobs")
def list_asset_collection_jobs(
    project_id: int, offset: int = Query(default=0, ge=0), limit: int = Query(default=5, ge=1, le=10),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    get_owned_project(db, project_id, user.id)
    jobs, total = list_asset_jobs(db, project_id, offset, limit)
    next_offset = offset + len(jobs)
    return {"jobs": jobs, "total": total, "next_offset": next_offset if next_offset < total else None}


@router.post("/{project_id}/asset-jobs/{job_id}/cancel")
def cancel_asset_collection_job(
    project_id: int, job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    get_owned_project(db, project_id, user.id)
    job = db.get(AssetJob, job_id)
    if job is None or job.project_id != project_id:
        raise HTTPException(status_code=404, detail="素材任务不存在")
    if job.status in {"pending", "running"}:
        job.status = "cancel_requested"
        db.commit()
    return asset_job_wire(job)


@router.post("/{project_id}/asset-jobs/{job_id}/retry")
async def retry_asset_collection_job(
    project_id: int, job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    get_owned_project(db, project_id, user.id)
    job = db.get(AssetJob, job_id)
    if job is None or job.project_id != project_id:
        raise HTTPException(status_code=404, detail="素材任务不存在")
    if job.status in {"pending", "running"}:
        raise HTTPException(status_code=409, detail="素材任务仍在运行")
    job.status, job.error, job.finished_at = "pending", None, None
    db.commit()
    await get_asset_task_manager().enqueue(partial(run_asset_job, job.id))
    return asset_job_wire(job)


@router.post("/{project_id}/asset-jobs/{job_id}/select")
async def select_asset_collection_candidate(
    project_id: int, job_id: int, candidate_index: int = Body(embed=True),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    get_owned_project(db, project_id, user.id)
    job = db.get(AssetJob, job_id)
    if job is None or job.project_id != project_id:
        raise HTTPException(status_code=404, detail="素材任务不存在")
    try:
        return {"asset": await select_asset_candidate(db, job, candidate_index)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, project_id, user.id)
    data = payload.model_dump(exclude_unset=True)
    tech_stack = data.pop("tech_stack", None)
    if tech_stack is not None and tech_stack != project.tech_stack:
        has_generated_content = (
            db.query(File).filter(File.project_id == project.id).first() is not None
            or db.query(Generation).filter(Generation.project_id == project.id).first() is not None
        )
        if has_generated_content:
            raise HTTPException(
                status_code=409,
                detail="项目已有生成内容，不能直接切换技术栈；请新建项目后重新生成",
            )
        old_workspace = project_workspace(project)
        project.tech_stack = tech_stack
        new_workspace = project_workspace(project)
        new_workspace.mkdir(parents=True, exist_ok=True)
        if old_workspace != new_workspace and old_workspace.exists():
            try:
                old_workspace.rmdir()
            except OSError:
                raise HTTPException(
                    status_code=409,
                    detail="旧工作区不是空目录，不能安全切换技术栈",
                )
    for key, value in data.items():
        if value is not None:
            setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return ProjectOut.model_validate(project)


@router.delete("/{project_id}", status_code=204)
def delete_project_endpoint(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, project_id, user.id)
    delete_project(db, project)
