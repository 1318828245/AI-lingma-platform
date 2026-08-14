"""基础实时预览：服务端代理生成产物（dist 或工作区静态文件）。"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, get_user_from_token
from app.models.file import File
from app.models.project import Project
from app.models.user import User
from app.services.project import get_owned_project, project_workspace

router = APIRouter(tags=["preview"])


def _preview_root(project_id: int) -> tuple[Path, str]:
    ws = project_workspace(project_id)
    dist = ws / "dist"
    if (dist / "index.html").exists():
        return dist, "dist"
    if (ws / "package.json").exists():
        return ws, "source"
    if (ws / "index.html").exists():
        return ws, "static"
    return ws, "empty"


@router.get("/api/projects/{project_id}/preview/status")
def preview_status(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_project(db, project_id, user.id)
    _, mode = _preview_root(project_id)
    if mode in ("dist", "static"):
        status = "ready"
    elif mode == "source":
        status = "not_generated"
    else:
        status = "empty"
    return {
        "status": status,
        "mode": mode,
        "url": f"/preview/{project_id}/",
    }


@router.get("/preview/{project_id}/{path:path}")
def preview_file(
    project_id: int,
    path: str,
    token: str = Query(..., description="访问令牌（iframe 无法带 header，使用 query）"),
    db: Session = Depends(get_db),
):
    user = get_user_from_token(db, token)
    project = get_owned_project(db, project_id, user.id)
    root, _ = _preview_root(project_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail="项目还没有可预览的内容")

    clean = path.replace("\\", "/").lstrip("/") or "index.html"
    target = (root / clean).resolve()
    root_resolved = root.resolve()
    if not target.is_relative_to(root_resolved):
        raise HTTPException(status_code=400, detail="路径越界")

    if target.is_dir():
        target = target / "index.html"
    if target.is_file():
        return FileResponse(target)
    # SPA fallback：非资源路径回退到 index.html
    index = root / "index.html"
    if index.exists() and not Path(clean).suffix:
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="文件不存在")


@router.get("/api/projects/{project_id}/files")
def list_project_files(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_project(db, project_id, user.id)
    rows = (
        db.query(File)
        .filter(File.project_id == project_id)
        .order_by(File.path.asc())
        .all()
    )
    return [
        {"path": row.path, "size": row.size, "content_hash": row.content_hash}
        for row in rows
    ]
