from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.project import Project
from app.models.file import File
from app.models.generation import Generation
from app.models.template import Template
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.project import create_project, delete_project, get_owned_project, project_workspace

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
