"""项目生命周期服务：创建（含模板落盘）、查询、删除（级联清理）。"""

import hashlib
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.deployment import Deployment
from app.models.evaluation import Evaluation
from app.models.file import File
from app.models.file_version import FileVersion
from app.models.generation import Generation
from app.models.guardrail import GuardrailEvent
from app.models.message import Message
from app.models.modification import Modification
from app.models.project import Project
from app.models.project_version import ProjectVersion
from app.models.session import Session as ChatSession
from app.models.template import Template
from app.schemas.project import ProjectCreate


_WORKSPACE_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-[0-9a-f]{8}$")


def make_project_slug(_name: str = "") -> str:
    """Create an ASCII-only storage identity independent from the display name."""
    return f"{datetime.now():%Y-%m-%d-%H-%M-%S}-{uuid.uuid4().hex[:8]}"


def workspace_name(project: Project) -> str:
    """Return the canonical storage identity, including a stable legacy fallback."""
    if _WORKSPACE_NAME_RE.fullmatch(project.slug):
        return project.slug
    created = project.created_at or datetime.now()
    digest = hashlib.sha256(f"{project.id}:{project.slug}".encode()).hexdigest()[:8]
    return f"{created:%Y-%m-%d-%H-%M-%S}-{digest}"


def project_thumbnail_path(project: Project) -> Path:
    return get_settings().storage_dir / "thumbnails" / f"{workspace_name(project)}.png"


def workspace_category(tech_stack: str) -> str:
    return "vue" if tech_stack.lower().startswith("vue") else "multifile"


def project_workspace(project: Project | int) -> Path:
    """Return the canonical ASCII-only workspace path."""
    settings = get_settings()
    if isinstance(project, Project):
        tech_stack = project.tech_stack
        name = workspace_name(project)
    else:
        project_id = project
        with SessionLocal() as db:
            row = db.get(Project, project_id)
            if row is None:
                return settings.workspace_dir / "multifile" / "missing-project"
            tech_stack = row.tech_stack
            name = workspace_name(row)
    return settings.workspace_dir / workspace_category(tech_stack) / name


def migrate_workspace_layout() -> int:
    """Move pre-standard workspaces into their canonical ASCII-only locations."""
    settings = get_settings()
    moved = 0
    with SessionLocal() as db:
        for project in db.query(Project).all():
            target = project_workspace(project)
            if target.exists():
                continue
            category = workspace_category(project.tech_stack)
            candidates = [
                settings.workspace_dir / category / project.slug,
                settings.workspace_dir / str(project.id),
            ]
            source = next((path for path in candidates if path.exists()), None)
            if source is not None:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(target))
                moved += 1
    return moved


def _content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def write_project_file(db: Session, project_id: int, rel_path: str, content: str) -> File:
    """写入工作区文件并登记元数据。路径只允许相对路径。"""
    settings = get_settings()
    clean = rel_path.replace("\\", "/").lstrip("/")
    if clean == "" or ".." in clean.split("/"):
        raise HTTPException(status_code=400, detail=f"非法文件路径: {rel_path}")
    project = db.get(Project, project_id)
    ws = project_workspace(project) if project is not None else project_workspace(project_id)
    target = (ws / clean).resolve()
    if not target.is_relative_to(ws.resolve()):
        raise HTTPException(status_code=400, detail=f"文件路径越界: {rel_path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode("utf-8")
    target.write_bytes(data)

    file_row = (
        db.query(File)
        .filter(File.project_id == project_id, File.path == clean)
        .first()
    )
    if file_row is None:
        file_row = File(project_id=project_id, path=clean, storage_path=clean)
        db.add(file_row)
    file_row.content_hash = _content_hash(data)
    file_row.size = len(data)
    db.flush()
    return file_row


def _copy_template_files(db: Session, project: Project, template: Template) -> None:
    files = template.files_json or {}
    for rel_path, content in files.items():
        write_project_file(db, project.id, rel_path, content)


def create_project(
    db: Session, owner_id: int, payload: ProjectCreate, template: Template | None
) -> Project:
    slug = make_project_slug(payload.name)
    while db.query(Project).filter(Project.slug == slug).first() is not None:
        slug = make_project_slug(payload.name)

    tech_stack = payload.tech_stack
    if template is not None:
        tech_stack = template.tech_stack
    project = Project(
        owner_id=owner_id,
        name=payload.name.strip(),
        slug=slug,
        description=payload.description.strip(),
        template=payload.template,
        tech_stack=tech_stack,
        status="active",
    )
    db.add(project)
    db.flush()

    ws = project_workspace(project)
    ws.mkdir(parents=True, exist_ok=True)
    if template is not None:
        _copy_template_files(db, project, template)

    session = ChatSession(
        user_id=owner_id,
        project_id=project.id,
        title=f"{project.name} 初始会话",
    )
    db.add(session)
    db.commit()
    db.refresh(project)
    return project


def get_owned_project(db: Session, project_id: int, user_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.owner_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问该项目")
    return project


def delete_project(db: Session, project: Project) -> None:
    """先清理各子表，再删除工作区目录。"""
    project_id = project.id
    session_ids = [
        row.id
        for row in db.query(ChatSession)
        .filter(ChatSession.project_id == project_id)
        .all()
    ]
    generation_ids = [
        row.id
        for row in db.query(Generation)
        .filter(Generation.project_id == project_id)
        .all()
    ]
    if session_ids:
        db.query(Message).filter(Message.session_id.in_(session_ids)).delete(
            synchronize_session=False
        )
    if generation_ids:
        db.query(Modification).filter(
            Modification.generation_id.in_(generation_ids)
        ).delete(synchronize_session=False)
    db.query(Modification).filter(Modification.project_id == project_id).delete(
        synchronize_session=False
    )
    db.query(Generation).filter(Generation.project_id == project_id).delete(
        synchronize_session=False
    )
    db.query(FileVersion).filter(
        FileVersion.file_id.in_(
            db.query(File.id).filter(File.project_id == project_id)
        )
    ).delete(synchronize_session=False)
    db.query(File).filter(File.project_id == project_id).delete(
        synchronize_session=False
    )
    db.query(ProjectVersion).filter(
        ProjectVersion.project_id == project_id
    ).delete(synchronize_session=False)
    db.query(Evaluation).filter(Evaluation.project_id == project_id).delete(
        synchronize_session=False
    )
    db.query(GuardrailEvent).filter(
        GuardrailEvent.project_id == project_id
    ).delete(synchronize_session=False)
    db.query(Deployment).filter(Deployment.project_id == project_id).delete(
        synchronize_session=False
    )
    db.query(ChatSession).filter(ChatSession.project_id == project_id).delete(
        synchronize_session=False
    )
    db.delete(project)
    db.commit()

    settings = get_settings()
    ws = project_workspace(project).resolve()
    if ws.is_relative_to(settings.workspace_dir.resolve()) and ws.exists():
        shutil.rmtree(ws)
    project_thumbnail_path(project).unlink(missing_ok=True)
    (settings.storage_dir / "thumbnails" / f"{project_id}.png").unlink(missing_ok=True)
    for root in (settings.versions_dir / workspace_name(project), settings.versions_dir / str(project_id)):
        if root.is_relative_to(settings.versions_dir.resolve()) and root.exists():
            shutil.rmtree(root)
