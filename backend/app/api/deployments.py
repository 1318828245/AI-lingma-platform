from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user, get_db
from app.models.deployment import Deployment
from app.models.project import Project
from app.models.user import User
from app.schemas.deployment import DeploymentCreate, DeploymentOut
from app.services.deployment import activate_deployment, create_deployment, get_deployment, list_deployments, offline_deployment
from app.services.project import get_owned_project
from app.services.audit import record_audit


router = APIRouter(tags=["deployments"])


def _site_url(project) -> str:
    return f"{get_settings().backend_url.rstrip('/')}/sites/{project.slug}/"


def _deployment_out(deployment: Deployment, project) -> dict:
    return {
        "id": deployment.id, "project_id": deployment.project_id, "version": deployment.version,
        "status": deployment.status, "url": deployment.url, "slug": deployment.slug,
        "error": deployment.error, "is_active": deployment.is_active,
        "site_url": _site_url(project) if deployment.is_active else None,
        "created_at": deployment.created_at, "updated_at": deployment.updated_at,
    }


@router.get("/api/projects/{project_id}/deployments", response_model=list[DeploymentOut])
def project_deployments(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = get_owned_project(db, project_id, user.id)
    return [_deployment_out(item, project) for item in list_deployments(db, project_id)]


@router.post("/api/projects/{project_id}/deployments", response_model=DeploymentOut)
def deploy_project(project_id: int, payload: DeploymentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = get_owned_project(db, project_id, user.id)
    deployment = create_deployment(db, project, user.id, payload.version_id)
    record_audit(db, actor_id=user.id, action="deployment.created", target_type="deployment", target_id=deployment.id, detail={"project_id": project.id, "version": deployment.version})
    db.commit()
    return _deployment_out(deployment, project)


@router.post("/api/projects/{project_id}/deployments/{deployment_id}/activate", response_model=DeploymentOut)
def activate_project_deployment(project_id: int, deployment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = get_owned_project(db, project_id, user.id)
    deployment = activate_deployment(db, project, deployment_id)
    record_audit(db, actor_id=user.id, action="deployment.activated", target_type="deployment", target_id=deployment.id, detail={"project_id": project.id, "version": deployment.version})
    db.commit()
    return _deployment_out(deployment, project)


@router.post("/api/projects/{project_id}/deployments/{deployment_id}/offline", response_model=DeploymentOut)
def offline_project_deployment(project_id: int, deployment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = get_owned_project(db, project_id, user.id)
    deployment = offline_deployment(db, project, deployment_id)
    record_audit(db, actor_id=user.id, action="deployment.offlined", target_type="deployment", target_id=deployment.id, detail={"project_id": project.id, "version": deployment.version})
    db.commit()
    return _deployment_out(deployment, project)


@router.get("/published/{slug}/{path:path}")
def published_file(slug: str, path: str, db: Session = Depends(get_db)):
    deployment = db.query(Deployment).filter(Deployment.slug == slug, Deployment.status == "ready").first()
    if deployment is None:
        raise HTTPException(status_code=404, detail="发布内容不存在或尚未就绪")
    root = (get_settings().publish_dir / slug).resolve()
    clean = path.replace("\\", "/").lstrip("/") or "index.html"
    target = (root / clean).resolve()
    if not target.is_relative_to(root):
        raise HTTPException(status_code=400, detail="路径越界")
    if target.is_dir():
        target = target / "index.html"
    if target.is_file():
        response = FileResponse(target)
    elif not Path(clean).suffix and (root / "index.html").is_file():
        response = FileResponse(root / "index.html")
    else:
        raise HTTPException(status_code=404, detail="发布文件不存在")
    response.headers["Cache-Control"] = "public, max-age=31536000, immutable" if clean.startswith("assets/") else "no-cache"
    return response


@router.get("/sites/{project_slug}/{path:path}")
def active_site_file(project_slug: str, path: str, db: Session = Depends(get_db)):
    deployment = (
        db.query(Deployment)
        .join(Project, Deployment.project_id == Project.id)
        .filter(Deployment.is_active.is_(True), Deployment.status == "ready")
        .filter(Project.slug == project_slug)
        .first()
    )
    if deployment is None:
        raise HTTPException(status_code=404, detail="项目当前没有在线发布版本")
    return published_file(deployment.slug, path, db)
