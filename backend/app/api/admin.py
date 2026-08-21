from functools import partial

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import get_settings
from app.core.deps import get_db, require_admin
from app.core.security import hash_password
from app.models.user import User
from app.models.project import Project
from app.models.generation import Generation
from app.models.modification import Modification
from app.models.asset import AssetJob
from app.models.deployment import Deployment
from app.models.audit import AuditLog
from app.schemas.user import ResetPasswordRequest, UserAdminUpdate, UserOut
from app.services.settings_store import settings_store
from app.services.audit import record_audit
from app.services.assets import asset_job_wire, run_asset_job
from app.services.deployment import activate_deployment, offline_deployment
from app.services.task_manager import get_asset_task_manager
from app.services.task_manager import get_task_manager

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/observability")
def observability(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Operational evidence without exposing credentials or request secrets."""
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        database = "healthy"
    except Exception:
        database = "unhealthy"
    generation_manager, asset_manager = get_task_manager(), get_asset_task_manager()
    projects = {item.id: item.name for item in db.query(Project).all()}
    timeline, alerts = [], []
    for row in db.query(Generation).order_by(Generation.created_at.desc()).limit(40):
        timeline.append({"id": f"generation-{row.id}", "project_id": row.project_id, "project_name": projects.get(row.project_id, f"项目 #{row.project_id}"), "stage": "生成", "status": row.status, "summary": row.requirement[:140], "error": row.error, "created_at": row.created_at, "finished_at": row.finished_at})
    for row in db.query(Modification).order_by(Modification.created_at.desc()).limit(40):
        timeline.append({"id": f"modification-{row.id}", "project_id": row.project_id, "project_name": projects.get(row.project_id, f"项目 #{row.project_id}"), "stage": "修改", "status": row.status, "summary": row.instruction[:140], "error": None, "created_at": row.created_at, "finished_at": row.finished_at})
    for row in db.query(AssetJob).order_by(AssetJob.created_at.desc()).limit(40):
        timeline.append({"id": f"asset-{row.id}", "project_id": row.project_id, "project_name": projects.get(row.project_id, f"项目 #{row.project_id}"), "stage": "素材采集", "status": row.status, "summary": (row.request_json or {}).get("query") or "素材采集", "error": row.error, "created_at": row.created_at, "finished_at": row.finished_at})
    for row in db.query(Deployment).order_by(Deployment.created_at.desc()).limit(40):
        timeline.append({"id": f"deployment-{row.id}", "project_id": row.project_id, "project_name": projects.get(row.project_id, f"项目 #{row.project_id}"), "stage": "发布", "status": row.status, "summary": f"版本 #{row.version}", "error": row.error, "created_at": row.created_at, "finished_at": None})
    timeline.sort(key=lambda item: item["created_at"], reverse=True)
    failed = [item for item in timeline if item["status"] in {"failed", "timed_out", "interrupted"} or item["error"]]
    for item in failed[:10]:
        alerts.append({"level": "critical", "title": f"{item['stage']}异常", "project_name": item["project_name"], "detail": item["error"] or f"任务状态：{item['status']}", "event_id": item["id"]})
    if generation_manager.queue_depth or asset_manager.queue_depth:
        alerts.append({"level": "warning", "title": "任务队列积压", "project_name": "平台", "detail": f"生成队列 {generation_manager.queue_depth}，素材队列 {asset_manager.queue_depth}", "event_id": "queue"})
    terminal = [item for item in timeline if item["status"] in {"succeeded", "failed", "timed_out", "interrupted", "ready", "offline"}]
    success = [item for item in terminal if item["status"] in {"succeeded", "ready", "offline"}]
    return {"health": [{"name": "后端 API", "status": "healthy", "detail": "服务正在响应"}, {"name": "数据库", "status": database, "detail": "SELECT 1 检查"}, {"name": "生成队列", "status": "healthy" if generation_manager.is_running else "unhealthy", "detail": f"等待任务 {generation_manager.queue_depth}"}, {"name": "素材队列", "status": "healthy" if asset_manager.is_running else "unhealthy", "detail": f"等待任务 {asset_manager.queue_depth}"}, {"name": "视觉评估", "status": "healthy" if settings.eval_vision_provider != "disabled" and bool(settings.eval_vision_api_key) else "degraded", "detail": "已配置" if settings.eval_vision_provider != "disabled" and bool(settings.eval_vision_api_key) else "未配置视觉模型"}, {"name": "素材来源", "status": "healthy" if any([settings.asset_pexels_api_key, settings.asset_pixabay_api_key, settings.asset_unsplash_access_key]) else "degraded", "detail": "至少一个来源已配置" if any([settings.asset_pexels_api_key, settings.asset_pixabay_api_key, settings.asset_unsplash_access_key]) else "未配置外部来源"}], "metrics": {"total_events": len(timeline), "success_rate": round(100 * len(success) / len(terminal), 1) if terminal else 100, "failed_events": len(failed), "queue_depth": generation_manager.queue_depth + asset_manager.queue_depth}, "alerts": alerts, "timeline": timeline[:100]}


@router.get("/overview")
def admin_overview(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.updated_at.desc()).limit(80).all()
    users = db.query(User).order_by(User.created_at.desc()).limit(80).all()
    deployments = db.query(Deployment).order_by(Deployment.created_at.desc()).limit(80).all()
    audits = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    project_names = {item.id: item.name for item in projects}
    task_rows = []
    for row in db.query(Generation).order_by(Generation.created_at.desc()).limit(30).all():
        task_rows.append({"id": f"generation-{row.id}", "kind": "生成", "project_id": row.project_id, "project_name": project_names.get(row.project_id, f"项目 #{row.project_id}"), "summary": row.requirement[:160], "status": row.status, "created_at": row.created_at, "error": row.error})
    for row in db.query(Modification).order_by(Modification.created_at.desc()).limit(30).all():
        task_rows.append({"id": f"modification-{row.id}", "kind": "修改", "project_id": row.project_id, "project_name": project_names.get(row.project_id, f"项目 #{row.project_id}"), "summary": row.instruction[:160], "status": row.status, "created_at": row.created_at, "error": None})
    for row in db.query(AssetJob).order_by(AssetJob.created_at.desc()).limit(30).all():
        request = row.request_json or {}
        task_rows.append({"id": f"asset-{row.id}", "kind": "素材", "project_id": row.project_id, "project_name": project_names.get(row.project_id, f"项目 #{row.project_id}"), "summary": request.get("query") or request.get("usage_role") or "素材采集", "status": row.status, "created_at": row.created_at, "error": row.error})
    task_rows.sort(key=lambda item: item["created_at"], reverse=True)
    return {
        "metrics": {"projects": db.query(Project).count(), "users": db.query(User).count(), "running_tasks": sum(1 for item in task_rows if item["status"] in {"pending", "running", "publishing"}), "online_sites": db.query(Deployment).filter(Deployment.is_active.is_(True), Deployment.status == "ready").count()},
        "projects": [{"id": item.id, "name": item.name, "owner": item.owner.username if item.owner else "-", "tech_stack": item.tech_stack, "status": item.status, "updated_at": item.updated_at} for item in projects],
        "users": [{"id": item.id, "username": item.username, "email": item.email, "role": item.role, "status": item.status, "quota": item.quota, "used_count": item.used_count, "created_at": item.created_at} for item in users],
        "tasks": task_rows[:60],
        "deployments": [{"id": item.id, "project_id": item.project_id, "project_name": project_names.get(item.project_id, f"项目 #{item.project_id}"), "version": item.version, "status": item.status, "is_active": item.is_active, "url": item.url, "created_at": item.created_at, "error": item.error} for item in deployments],
        "audits": [{"id": item.id, "actor_id": item.actor_id, "action": item.action, "target_type": item.target_type, "target_id": item.target_id, "detail": item.detail_json, "created_at": item.created_at} for item in audits],
    }


class AdminSettingsIn(BaseModel):
    register_enabled: bool | None = None
    default_user_quota: int | None = Field(default=None, ge=0, le=100000)


class AdminSettingsOut(BaseModel):
    app_name: str
    environment: str
    register_enabled: bool
    default_user_quota: int


@router.get("/settings", response_model=AdminSettingsOut)
def get_settings_admin(
    admin: User = Depends(require_admin),
):
    settings = get_settings()
    return AdminSettingsOut(
        app_name=settings.app_name,
        environment=settings.environment,
        register_enabled=bool(
            settings_store.get("register_enabled", settings.register_enabled)
        ),
        default_user_quota=int(
            settings_store.get("default_user_quota", settings.default_user_quota)
        ),
    )


@router.put("/settings", response_model=AdminSettingsOut)
def update_settings_admin(
    payload: AdminSettingsIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        settings_store.set(key, value)
    if data:
        record_audit(db, actor_id=admin.id, action="settings.updated", target_type="settings", target_id="platform", detail=data)
        db.commit()
    settings = get_settings()
    return AdminSettingsOut(
        app_name=settings.app_name,
        environment=settings.environment,
        register_enabled=bool(
            settings_store.get("register_enabled", settings.register_enabled)
        ),
        default_user_quota=int(
            settings_store.get("default_user_quota", settings.default_user_quota)
        ),
    )


@router.get("/users", response_model=list[UserOut])
def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(User).order_by(User.created_at.asc()).all()


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserAdminUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.id == admin.id and (
        (payload.role is not None and payload.role != "admin")
        or (payload.status is not None and payload.status != "active")
    ):
        raise HTTPException(status_code=400, detail="不能降级或禁用当前登录的管理员")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if value is not None:
            setattr(target, key, value)
    if data:
        record_audit(db, actor_id=admin.id, action="user.updated", target_type="user", target_id=target.id, detail=data)
    db.commit()
    db.refresh(target)
    return UserOut.model_validate(target)


@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    payload: ResetPasswordRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    target.password_hash = hash_password(payload.new_password)
    record_audit(db, actor_id=admin.id, action="user.password_reset", target_type="user", target_id=target.id)
    db.commit()
    return {"ok": True}


@router.post("/asset-jobs/{job_id}/retry")
async def retry_asset_job_admin(job_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    job = db.get(AssetJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="素材任务不存在")
    if job.status in {"pending", "running"}:
        raise HTTPException(status_code=409, detail="素材任务仍在运行")
    job.status, job.error, job.finished_at = "pending", None, None
    record_audit(db, actor_id=admin.id, action="asset_job.retried", target_type="asset_job", target_id=job.id, detail={"project_id": job.project_id})
    db.commit()
    await get_asset_task_manager().enqueue(partial(run_asset_job, job.id))
    return asset_job_wire(job)


@router.post("/deployments/{deployment_id}/activate")
def activate_deployment_admin(deployment_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    deployment = db.get(Deployment, deployment_id)
    if deployment is None:
        raise HTTPException(status_code=404, detail="发布记录不存在")
    project = db.get(Project, deployment.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    deployment = activate_deployment(db, project, deployment_id)
    record_audit(db, actor_id=admin.id, action="deployment.activated", target_type="deployment", target_id=deployment.id, detail={"project_id": project.id, "version": deployment.version, "by": "admin"})
    db.commit()
    return {"id": deployment.id, "status": deployment.status, "is_active": deployment.is_active}


@router.post("/deployments/{deployment_id}/offline")
def offline_deployment_admin(deployment_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    deployment = db.get(Deployment, deployment_id)
    if deployment is None:
        raise HTTPException(status_code=404, detail="发布记录不存在")
    project = db.get(Project, deployment.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    deployment = offline_deployment(db, project, deployment_id)
    record_audit(db, actor_id=admin.id, action="deployment.offlined", target_type="deployment", target_id=deployment.id, detail={"project_id": project.id, "version": deployment.version, "by": "admin"})
    db.commit()
    return {"id": deployment.id, "status": deployment.status, "is_active": deployment.is_active}
