from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user, get_db
from app.models.deployment import Deployment
from app.models.user import User
from app.schemas.deployment import DeploymentCreate, DeploymentOut
from app.services.deployment import create_deployment, list_deployments
from app.services.project import get_owned_project


router = APIRouter(tags=["deployments"])


@router.get("/api/projects/{project_id}/deployments", response_model=list[DeploymentOut])
def project_deployments(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_owned_project(db, project_id, user.id)
    return list_deployments(db, project_id)


@router.post("/api/projects/{project_id}/deployments", response_model=DeploymentOut)
def deploy_project(project_id: int, payload: DeploymentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = get_owned_project(db, project_id, user.id)
    return create_deployment(db, project, user.id, payload.version_id)


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
