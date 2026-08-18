"""项目版本快照、差异和回滚。内容存磁盘，数据库只保存索引和清单。"""

import difflib
import hashlib
import shutil
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.file import File
from app.models.file_version import FileVersion
from app.models.project_version import ProjectVersion
from app.services.project import project_workspace


def _safe_relative(path: str) -> str:
    clean = path.replace("\\", "/").lstrip("/")
    if not clean or ".." in clean.split("/"):
        raise HTTPException(status_code=400, detail=f"非法文件路径: {path}")
    return clean


def _version_root(project_id: int, version_no: int) -> Path:
    root = get_settings().versions_dir / str(project_id) / f"v{version_no}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _workspace_files(project_id: int) -> list[tuple[str, Path]]:
    workspace = project_workspace(project_id).resolve()
    if not workspace.exists():
        return []
    result: list[tuple[str, Path]] = []
    for path in workspace.rglob("*"):
        if path.is_file():
            if path.is_symlink():
                raise HTTPException(status_code=400, detail="工作区包含不允许的符号链接")
            result.append((path.relative_to(workspace).as_posix(), path))
    return sorted(result)


def _next_version_no(db: Session, project_id: int) -> int:
    latest = (
        db.query(ProjectVersion)
        .filter(ProjectVersion.project_id == project_id)
        .order_by(ProjectVersion.version_no.desc())
        .first()
    )
    return (latest.version_no + 1) if latest else 1


def snapshot_project(
    db: Session,
    project_id: int,
    *,
    source_type: str = "generation",
    source_id: int | None = None,
    summary: str | None = None,
) -> ProjectVersion:
    version_no = _next_version_no(db, project_id)
    root = _version_root(project_id, version_no)
    versions_dir = get_settings().versions_dir.resolve()
    manifest: dict[str, dict[str, int | str]] = {}
    file_rows = {
        row.path: row
        for row in db.query(File).filter(File.project_id == project_id).all()
    }

    for rel_path, source in _workspace_files(project_id):
        clean = _safe_relative(rel_path)
        target = (root / clean).resolve()
        if not target.is_relative_to(root.resolve()):
            raise HTTPException(status_code=400, detail=f"文件路径越界: {rel_path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        data = source.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        storage_path = target.relative_to(versions_dir).as_posix()
        manifest[clean] = {"hash": digest, "size": len(data), "storage_path": storage_path}

        file_row = file_rows.get(clean)
        if file_row is None:
            file_row = File(
                project_id=project_id,
                path=clean,
                content_hash=digest,
                size=len(data),
                storage_path=clean,
            )
            db.add(file_row)
            db.flush()
        db.add(
            FileVersion(
                file_id=file_row.id,
                version_no=version_no,
                storage_path=storage_path,
                size=len(data),
                created_by=source_type,
                comment=summary,
            )
        )

    version = ProjectVersion(
        project_id=project_id,
        version_no=version_no,
        snapshot_manifest_json=manifest,
        source_type=source_type,
        source_id=source_id,
        summary=summary,
    )
    db.add(version)
    db.flush()
    return version


def list_versions(db: Session, project_id: int) -> list[ProjectVersion]:
    return (
        db.query(ProjectVersion)
        .filter(ProjectVersion.project_id == project_id)
        .order_by(ProjectVersion.version_no.desc())
        .all()
    )


def get_version(db: Session, project_id: int, version_id: int) -> ProjectVersion:
    version = db.get(ProjectVersion, version_id)
    if version is None or version.project_id != project_id:
        raise HTTPException(status_code=404, detail="项目版本不存在")
    return version


def version_manifest(version: ProjectVersion) -> dict[str, dict]:
    return version.snapshot_manifest_json or {}


def _read_version_files(version: ProjectVersion) -> dict[str, str]:
    versions_dir = get_settings().versions_dir.resolve()
    result = {}
    for rel_path, metadata in version_manifest(version).items():
        stored = (get_settings().versions_dir / str(metadata["storage_path"])).resolve()
        if not stored.is_relative_to(versions_dir) or not stored.is_file():
            raise HTTPException(status_code=500, detail=f"版本文件缺失: {rel_path}")
        result[rel_path] = stored.read_text(encoding="utf-8")
    return result


def version_diff(db: Session, project_id: int, version: ProjectVersion) -> list[dict[str, str]]:
    current = {
        path: source.read_text(encoding="utf-8")
        for path, source in _workspace_files(project_id)
    }
    target = _read_version_files(version)
    result = []
    for path in sorted(set(current) | set(target)):
        before, after = current.get(path, ""), target.get(path, "")
        if before == after:
            continue
        status = "added" if path not in current else "deleted" if path not in target else "modified"
        diff = "".join(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile=f"current/{path}", tofile=f"version-{version.version_no}/{path}",
        ))
        result.append({"path": path, "status": status, "diff": diff})
    return result


def rollback_project(db: Session, project_id: int, version: ProjectVersion) -> list[str]:
    workspace = project_workspace(project_id).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    versions_dir = get_settings().versions_dir.resolve()
    target_files = {}
    for rel_path, metadata in version_manifest(version).items():
        clean = _safe_relative(rel_path)
        stored = (get_settings().versions_dir / str(metadata["storage_path"])).resolve()
        if not stored.is_relative_to(versions_dir) or not stored.is_file():
            raise HTTPException(status_code=500, detail=f"版本文件缺失: {clean}")
        target_files[clean] = stored

    for _, path in _workspace_files(project_id):
        path.unlink()
    for clean, stored in target_files.items():
        destination = (workspace / clean).resolve()
        if not destination.is_relative_to(workspace):
            raise HTTPException(status_code=400, detail=f"文件路径越界: {clean}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(stored, destination)

    rows = {row.path: row for row in db.query(File).filter(File.project_id == project_id).all()}
    for path, row in rows.items():
        if path not in target_files:
            db.query(FileVersion).filter(FileVersion.file_id == row.id).delete(
                synchronize_session=False
            )
            db.delete(row)
    for clean, stored in target_files.items():
        data = stored.read_bytes()
        row = rows.get(clean)
        if row is None:
            row = File(project_id=project_id, path=clean, storage_path=clean)
            db.add(row)
        row.content_hash = hashlib.sha256(data).hexdigest()
        row.size = len(data)
    db.commit()
    return sorted(target_files)
