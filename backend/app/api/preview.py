"""基础实时预览：服务端代理生成产物（dist 或工作区静态文件）。"""

from pathlib import Path

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import (
    get_current_user,
    get_current_user_sse,
    get_db,
    get_user_from_token,
)
from app.core.security import create_access_token
from app.models.file import File
from app.models.project import Project
from app.models.user import User
from app.services.screenshot import capture_screenshot
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
    token: str | None = Query(default=None, description="访问令牌（兼容旧链接）"),
    preview_token: str | None = Cookie(default=None, description="iframe 静态资源鉴权 Cookie"),
    db: Session = Depends(get_db),
):
    auth_token = token or preview_token
    if not auth_token:
        raise HTTPException(status_code=401, detail="缺少预览令牌")
    user = get_user_from_token(db, auth_token)
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
        response = FileResponse(target)
    elif (root / "index.html").exists() and not Path(clean).suffix:
        response = FileResponse(root / "index.html")
    else:
        raise HTTPException(status_code=404, detail="文件不存在")
    # SPA fallback：非资源路径回退到 index.html
    if token:
        # 让无头浏览器/iframe 的静态资源自动带上鉴权 Cookie
        response.headers["Set-Cookie"] = (
            f"preview_token={auth_token}; Path=/preview; SameSite=Lax; Max-Age=86400"
        )
    return response


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


@router.get("/api/projects/{project_id}/screenshot")
async def project_screenshot(
    project_id: int,
    force: bool = Query(default=False),
    user: User = Depends(get_current_user_sse),
    db: Session = Depends(get_db),
):
    """首页项目截图：首次访问时生成并缓存，产物变化后自动重建。"""
    get_owned_project(db, project_id, user.id)
    root, mode = _preview_root(project_id)
    if mode not in ("dist", "static"):
        raise HTTPException(status_code=404, detail="项目尚未生成可预览内容")
    index = root / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="项目尚未生成可预览内容")

    thumb = get_settings().storage_dir / "thumbnails" / f"{project_id}.png"
    if force and thumb.exists():
        thumb.unlink(missing_ok=True)
    index_mtime = index.stat().st_mtime
    if not thumb.exists() or thumb.stat().st_mtime < index_mtime:
        token = create_access_token(user.id)
        url = (
            f"{get_settings().backend_url.rstrip('/')}"
            f"/preview/{project_id}/?token={token}"
        )
        ok = await capture_screenshot(url, thumb)
        if not ok:
            raise HTTPException(status_code=404, detail="截图生成失败（环境不支持或无浏览器）")
    return FileResponse(thumb, media_type="image/png")
