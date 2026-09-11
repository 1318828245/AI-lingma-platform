from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user, get_db
from app.models.deployment import Deployment
from app.models.project import Project
from app.models.user import User
from app.schemas.deployment import DeploymentCreate, DeploymentOut
from app.services.deployment import activate_deployment, create_deployment, get_deployment, list_deployments, offline_deployment, rebuild_and_deploy
from app.services.project import get_owned_project
from app.services.audit import record_audit


router = APIRouter(tags=["deployments"])


def _public_base_url(request: Request) -> str:
    configured = get_settings().public_base_url.strip().rstrip("/")
    return configured or str(request.base_url).rstrip("/")


def _deployment_out(deployment: Deployment, project, request: Request) -> dict:
    public_base_url = _public_base_url(request)
    return {
        "id": deployment.id, "project_id": deployment.project_id, "version": deployment.version,
        "status": deployment.status, "url": f"{public_base_url}/published/{deployment.slug}/", "slug": deployment.slug,
        "error": deployment.error, "is_active": deployment.is_active,
        "site_url": f"{public_base_url}/sites/{project.slug}/" if deployment.is_active else None,
        "created_at": deployment.created_at, "updated_at": deployment.updated_at,
    }


@router.get("/api/projects/{project_id}/deployments", response_model=list[DeploymentOut])
def project_deployments(project_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = get_owned_project(db, project_id, user.id)
    return [_deployment_out(item, project, request) for item in list_deployments(db, project_id)]


@router.post("/api/projects/{project_id}/deployments", response_model=DeploymentOut)
def deploy_project(project_id: int, payload: DeploymentCreate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = get_owned_project(db, project_id, user.id)
    deployment = create_deployment(db, project, user.id, payload.version_id)
    record_audit(db, actor_id=user.id, action="deployment.created", target_type="deployment", target_id=deployment.id, detail={"project_id": project.id, "version": deployment.version})
    db.commit()
    return _deployment_out(deployment, project, request)


@router.post("/api/projects/{project_id}/deployments/rebuild-and-publish", response_model=DeploymentOut)
async def rebuild_and_publish_project(project_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The user-facing deployment path: build, snapshot, and make it live in one request."""
    project = get_owned_project(db, project_id, user.id)
    deployment, _log, errors = await rebuild_and_deploy(db, project, user.id)
    if deployment is None:
        raise HTTPException(status_code=422, detail={"message": "构建失败，未创建发布版本", "errors": errors[-20:]})
    record_audit(db, actor_id=user.id, action="deployment.rebuilt_and_published", target_type="deployment", target_id=deployment.id, detail={"project_id": project.id, "version": deployment.version})
    db.commit()
    return _deployment_out(deployment, project, request)


@router.post("/api/projects/{project_id}/deployments/{deployment_id}/activate", response_model=DeploymentOut)
def activate_project_deployment(project_id: int, deployment_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = get_owned_project(db, project_id, user.id)
    deployment = activate_deployment(db, project, deployment_id)
    record_audit(db, actor_id=user.id, action="deployment.activated", target_type="deployment", target_id=deployment.id, detail={"project_id": project.id, "version": deployment.version})
    db.commit()
    return _deployment_out(deployment, project, request)


@router.post("/api/projects/{project_id}/deployments/{deployment_id}/offline", response_model=DeploymentOut)
def offline_project_deployment(project_id: int, deployment_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = get_owned_project(db, project_id, user.id)
    deployment = offline_deployment(db, project, deployment_id)
    record_audit(db, actor_id=user.id, action="deployment.offlined", target_type="deployment", target_id=deployment.id, detail={"project_id": project.id, "version": deployment.version})
    db.commit()
    return _deployment_out(deployment, project, request)


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
