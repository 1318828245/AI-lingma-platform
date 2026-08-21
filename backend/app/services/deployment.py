"""Immutable static delivery from a project's version snapshot."""

import re
import shutil
import unicodedata
import uuid
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.deployment import Deployment
from app.models.project import Project
from app.models.project_version import ProjectVersion
from app.services.version import get_version, list_versions, version_manifest


def _deployment_slug(project: Project, version: ProjectVersion) -> str:
    normalized = unicodedata.normalize("NFKD", project.name).encode("ascii", "ignore").decode()
    stem = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-") or "project"
    return f"{stem[:32]}-v{version.version_no}-{uuid.uuid4().hex[:6]}"


def list_deployments(db: Session, project_id: int) -> list[Deployment]:
    return (
        db.query(Deployment)
        .filter(Deployment.project_id == project_id)
        .order_by(Deployment.created_at.desc(), Deployment.id.desc())
        .all()
    )


def _selected_version(db: Session, project_id: int, version_id: int | None) -> ProjectVersion:
    if version_id is not None:
        return get_version(db, project_id, version_id)
    versions = list_versions(db, project_id)
    if not versions:
        raise HTTPException(status_code=400, detail="请先完成一次成功构建，再发布项目")
    return versions[0]


_STATIC_EXCLUDED_NAMES = {"package.json", "package-lock.json", "vite.config.js"}
_STATIC_EXCLUDED_PREFIXES = ("node_modules/", ".git/", "__pycache__/")


def _copy_delivery(version: ProjectVersion, destination: Path) -> None:
    settings = get_settings()
    versions_root = settings.versions_dir.resolve()
    manifest = version_manifest(version)
    dist_files = [(path, data) for path, data in manifest.items() if path.startswith("dist/")]
    # Vue/Vite projects publish their immutable build directory. Plain HTML
    # projects are already a static delivery, so publish their root files.
    if dist_files:
        publish_files = [(path.removeprefix("dist/"), data) for path, data in dist_files]
    else:
        publish_files = [
            (path, data)
            for path, data in manifest.items()
            if not path.startswith(_STATIC_EXCLUDED_PREFIXES)
            and Path(path).name not in _STATIC_EXCLUDED_NAMES
        ]
    if not any(path == "index.html" for path, _ in publish_files):
        raise ValueError("该版本没有可发布的 index.html 交付物")
    for relative, metadata in publish_files:
        source = (versions_root / str(metadata["storage_path"])).resolve()
        if not source.is_relative_to(versions_root) or not source.is_file():
            raise ValueError(f"发布快照文件不可用：{relative}")
        target = (destination / relative).resolve()
        if not target.is_relative_to(destination.resolve()):
            raise ValueError("发布文件路径不安全")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    if not (destination / "index.html").is_file():
        raise ValueError("发布产物缺少 index.html")


def create_deployment(
    db: Session, project: Project, user_id: int, version_id: int | None = None
) -> Deployment:
    version = _selected_version(db, project.id, version_id)
    deployment = Deployment(
        project_id=project.id,
        version=version.version_no,
        status="publishing",
        slug=_deployment_slug(project, version),
        created_by=user_id,
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    publish_root = get_settings().publish_dir.resolve()
    destination = (publish_root / deployment.slug).resolve()
    staging = (publish_root / f".{deployment.slug}.staging").resolve()
    try:
        if not destination.is_relative_to(publish_root) or not staging.is_relative_to(publish_root):
            raise ValueError("发布目录不安全")
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=False)
        _copy_delivery(version, staging)
        if destination.exists():
            raise ValueError("发布地址已存在，请重新发布")
        staging.replace(destination)
        deployment.status = "ready"
        deployment.url = f"{get_settings().backend_url.rstrip('/')}/published/{deployment.slug}/"
        deployment.error = None
    except Exception as exc:
        shutil.rmtree(staging, ignore_errors=True)
        deployment.status = "failed"
        deployment.error = str(exc)[:2000]
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    return deployment
