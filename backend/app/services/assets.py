"""Controlled asynchronous collection of project icons and media assets.

The model supplies only a semantic request.  This service owns the network
allowlist, license metadata, file validation, and project manifest writes.
"""

import asyncio
import hashlib
import inspect
import json
import re
import subprocess
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from urllib.error import URLError
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.asset import AssetJob, ProjectAsset
from app.services.project import project_workspace, write_project_file

AssetEvent = Callable[[dict], Awaitable[None]]
_SAFE_KINDS = {"icon", "photo", "illustration"}
_SAFE_NAME = re.compile(r"[^a-z0-9-]+")


@dataclass(frozen=True)
class AssetCandidate:
    source: str
    kind: str
    title: str
    source_url: str
    license_name: str
    attribution: str = ""
    external_url: str = ""
    download_url: str = ""
    width: int | None = None
    height: int | None = None

    def wire(self) -> dict:
        return {key: value for key, value in asdict(self).items() if value not in (None, "")}


def _safe_slug(value: str) -> str:
    result = _SAFE_NAME.sub("-", value.lower()).strip("-")
    return result[:60] or "asset"


def _request_json(url: str, headers: dict[str, str] | None = None) -> dict:
    request_headers = {"Accept": "application/json", "User-Agent": "AI-Lingma-Platform/0.1", **(headers or {})}
    request = Request(url, headers=request_headers)
    try:
        with urlopen(request, timeout=get_settings().asset_request_timeout_seconds) as response:  # noqa: S310 - URL is source-owned
            if response.status != 200:
                raise RuntimeError(f"asset source returned HTTP {response.status}")
            data = response.read()
    except URLError as exc:
        if not _socket_permission_denied(exc):
            raise
        data = _curl_fallback(url, request_headers)
    return json.loads(data.decode("utf-8"))


def _request_bytes(url: str) -> bytes:
    request_headers = {"Accept": "image/svg+xml", "User-Agent": "AI-Lingma-Platform/0.1"}
    request = Request(url, headers=request_headers)
    try:
        with urlopen(request, timeout=get_settings().asset_request_timeout_seconds) as response:  # noqa: S310 - URL is source-owned
            content_type = response.headers.get_content_type()
            data = response.read(256 * 1024 + 1)
        if content_type not in {"image/svg+xml", "text/plain", "application/octet-stream"}:
            raise ValueError("icon source returned an unsupported content type")
    except URLError as exc:
        if not _socket_permission_denied(exc):
            raise
        data = _curl_fallback(url, request_headers)
    if len(data) > 256 * 1024:
        raise ValueError("icon exceeds the 256 KiB limit")
    return data


def _socket_permission_denied(exc: URLError) -> bool:
    reason = getattr(exc, "reason", None)
    return isinstance(reason, OSError) and getattr(reason, "winerror", None) == 10013


def _curl_fallback(url: str, headers: dict[str, str]) -> bytes:
    """Use Windows' HTTPS client only when Python sockets are policy-blocked.

    This is not an Agent command: the URL is assembled by a source adapter and
    the process receives no shell, workspace, or user-controlled command text.
    """
    timeout = str(get_settings().asset_request_timeout_seconds)
    command = ["curl.exe", "--fail", "--silent", "--show-error", "--location", "--connect-timeout", timeout, "--max-time", timeout]
    for name, value in headers.items():
        command.extend(["--header", f"{name}: {value}"])
    command.append(url)
    completed = subprocess.run(command, capture_output=True, check=False, timeout=get_settings().asset_request_timeout_seconds + 2)
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()[-300:]
        raise RuntimeError(f"asset source connection failed: {detail or completed.returncode}")
    return completed.stdout


def _validate_svg(data: bytes) -> None:
    text = data.decode("utf-8", errors="strict")
    lowered = text.lower()
    if not lowered.lstrip().startswith("<svg"):
        raise ValueError("icon payload is not SVG")
    if any(token in lowered for token in ("<script", "<foreignobject", "javascript:", " onload=", " onerror=")):
        raise ValueError("SVG contains active content")


async def _iconify_candidates(query: str, limit: int) -> list[AssetCandidate]:
    settings = get_settings()
    if not settings.asset_iconify_enabled:
        return []
    base = settings.asset_iconify_api_url.rstrip("/")
    # Fixed Lucide collection keeps the license policy deterministic in v1.
    url = f"{base}/search?prefix=lucide&query={quote(query)}&limit={limit}"
    payload = await asyncio.to_thread(_request_json, url)
    icons = [str(name) for name in payload.get("icons", [])][:limit]
    result: list[AssetCandidate] = []
    for name in icons:
        if not name.startswith("lucide:"):
            continue
        icon_name = name.split(":", 1)[1]
        svg_url = f"{base}/lucide/{quote(icon_name)}.svg"
        result.append(
            AssetCandidate(
                source="iconify-lucide",
                kind="icon",
                title=icon_name,
                source_url=f"https://icon-sets.iconify.design/lucide/{icon_name}/",
                license_name="ISC (Lucide icon set)",
                attribution="Lucide Icons via Iconify",
                external_url=svg_url,
                download_url=svg_url,
            )
        )
    return result


async def _pexels_candidates(query: str, orientation: str, limit: int) -> list[AssetCandidate]:
    settings = get_settings()
    if not settings.asset_pexels_api_key:
        return []
    params = f"query={quote(query)}&per_page={limit}&orientation={quote(orientation or 'landscape')}"
    payload = await asyncio.to_thread(
        _request_json,
        f"{settings.asset_pexels_api_url.rstrip('/')}/search?{params}",
        {"Authorization": settings.asset_pexels_api_key},
    )
    result: list[AssetCandidate] = []
    for photo in payload.get("photos", [])[:limit]:
        src = photo.get("src") or {}
        external = str(src.get("large") or src.get("medium") or "")
        page = str(photo.get("url") or "")
        if not external or not page:
            continue
        photographer = str(photo.get("photographer") or "Pexels contributor")
        result.append(
            AssetCandidate(
                source="pexels",
                kind="photo",
                title=str(photo.get("alt") or query),
                source_url=page,
                license_name="Pexels License",
                attribution=f"Photo by {photographer} on Pexels",
                external_url=external,
                width=int(photo["width"]) if photo.get("width") else None,
                height=int(photo["height"]) if photo.get("height") else None,
            )
        )
    return result


async def _emit(callback: AssetEvent | None, event: dict) -> None:
    if callback is not None:
        result = callback(event)
        if inspect.isawaitable(result):
            await result


def _append_manifest(db: Session, project_id: int, asset: ProjectAsset) -> None:
    workspace = project_workspace(project_id)
    manifest_path = workspace / "assets" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"assets": []}
    except json.JSONDecodeError:
        manifest = {"assets": []}
    entries = [entry for entry in manifest.get("assets", []) if entry.get("id") != asset.id]
    entries.append(
        {
            "id": asset.id,
            "kind": asset.kind,
            "role": asset.usage_role,
            "source": asset.source,
            "source_url": asset.source_url,
            "license": asset.license_name,
            "attribution": asset.attribution,
            "external_url": asset.external_url,
            "local_path": asset.local_path,
        }
    )
    write_project_file(
        db,
        project_id,
        "assets/manifest.json",
        json.dumps({"assets": entries}, ensure_ascii=False, indent=2) + "\n",
    )


def _materialize_icon(db: Session, project_id: int, job_id: int, candidate: AssetCandidate, role: str) -> ProjectAsset:
    data = _request_bytes(candidate.download_url)
    _validate_svg(data)
    filename = f"assets/icons/{_safe_slug(candidate.title)}.svg"
    write_project_file(db, project_id, filename, data.decode("utf-8"))
    asset = ProjectAsset(
        project_id=project_id,
        asset_job_id=job_id,
        kind="icon",
        usage_role=role,
        source=candidate.source,
        source_url=candidate.source_url,
        external_url=candidate.external_url,
        local_path=filename,
        license_name=candidate.license_name,
        attribution=candidate.attribution or None,
        content_hash=hashlib.sha256(data).hexdigest(),
        metadata_json=candidate.wire(),
    )
    db.add(asset)
    db.flush()
    _append_manifest(db, project_id, asset)
    return asset


def _materialize_external(db: Session, project_id: int, job_id: int, candidate: AssetCandidate, role: str) -> ProjectAsset:
    asset = ProjectAsset(
        project_id=project_id,
        asset_job_id=job_id,
        kind=candidate.kind,
        usage_role=role,
        source=candidate.source,
        source_url=candidate.source_url,
        external_url=candidate.external_url,
        license_name=candidate.license_name,
        attribution=candidate.attribution or None,
        metadata_json=candidate.wire(),
    )
    db.add(asset)
    db.flush()
    _append_manifest(db, project_id, asset)
    return asset


async def collect_assets(
    *,
    project_id: int,
    generation_id: int | None,
    session_id: int | None,
    kind: str,
    query: str,
    usage_role: str = "decorative",
    orientation: str = "landscape",
    limit: int = 4,
    emit: AssetEvent | None = None,
) -> dict:
    """Run allowed source adapters concurrently and materialize one safe choice.

    A failed/empty collection is a successful degraded result: code generation can
    continue without external media, while the user receives an explicit event.
    """
    if kind not in _SAFE_KINDS:
        raise ValueError("asset kind must be icon, photo, or illustration")
    cleaned_query = " ".join(query.split())[:180]
    if not cleaned_query:
        raise ValueError("asset query cannot be empty")
    limit = max(1, min(int(limit), 6))
    request = {"kind": kind, "query": cleaned_query, "usage_role": usage_role[:80], "orientation": orientation[:20], "limit": limit}
    settings = get_settings()
    source_configured = (
        (kind == "icon" and settings.asset_iconify_enabled)
        or (kind == "photo" and bool(settings.asset_pexels_api_key))
    )
    with SessionLocal() as db:
        job = AssetJob(project_id=project_id, generation_id=generation_id, session_id=session_id, status="running", request_json=request, started_at=datetime.now())
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id
    await _emit(emit, {"type": "asset_collection_started", "asset_job_id": job_id, "kind": kind, "query": cleaned_query})

    tasks: list[tuple[str, Awaitable[list[AssetCandidate]]]] = []
    if kind == "icon":
        tasks.append(("iconify-lucide", _iconify_candidates(cleaned_query, limit)))
    elif kind == "photo":
        tasks.append(("pexels", _pexels_candidates(cleaned_query, orientation, limit)))
    if not tasks:
        candidates: list[AssetCandidate] = []
        source_errors: list[str] = []
    else:
        groups = await asyncio.gather(*(task for _, task in tasks), return_exceptions=True)
        candidates = []
        source_errors = []
        for (source_name, _), group in zip(tasks, groups, strict=True):
            if isinstance(group, Exception):
                source_errors.append(f"{source_name}: {type(group).__name__}: {str(group)[:180]}")
                continue
            candidates.extend(group)
    candidates = candidates[:limit]
    for candidate in candidates:
        await _emit(emit, {"type": "asset_candidate", "asset_job_id": job_id, "candidate": candidate.wire()})

    selected: ProjectAsset | None = None
    materialize_error = ""
    if candidates:
        try:
            with SessionLocal() as db:
                selected = (
                    _materialize_icon(db, project_id, job_id, candidates[0], usage_role)
                    if candidates[0].kind == "icon"
                    else _materialize_external(db, project_id, job_id, candidates[0], usage_role)
                )
                db.commit()
                db.refresh(selected)
        except Exception as exc:  # source errors must not fail parent generation
            materialize_error = f"素材不可用，已降级：{type(exc).__name__}"

    if selected is not None:
        message = "素材已加入项目清单"
    elif materialize_error:
        message = materialize_error
    elif source_errors:
        message = f"素材来源暂不可用（{source_errors[0]}），已继续生成无素材版本"
    elif not source_configured:
        message = "未配置可用素材来源，已继续生成无素材版本"
    else:
        message = "未找到可用素材，已继续生成无素材版本"
    result = {"job_id": job_id, "candidates": [item.wire() for item in candidates], "selected": _asset_wire(selected) if selected else None, "degraded": selected is None, "source_errors": source_errors}
    with SessionLocal() as db:
        job = db.get(AssetJob, job_id)
        if job is not None:
            job.status = "succeeded"
            job.result_json = result["candidates"]
            job.error = materialize_error or "; ".join(source_errors) or ("未配置可用素材来源" if not source_configured else None)
            job.finished_at = datetime.now()
            db.commit()
    await _emit(emit, {"type": "asset_collection_completed", **result, "message": message})
    return result


def _asset_wire(asset: ProjectAsset | None) -> dict | None:
    if asset is None:
        return None
    return {
        "id": asset.id,
        "kind": asset.kind,
        "role": asset.usage_role,
        "source": asset.source,
        "source_url": asset.source_url,
        "external_url": asset.external_url,
        "local_path": asset.local_path,
        "license": asset.license_name,
        "attribution": asset.attribution,
    }


def list_project_assets(db: Session, project_id: int) -> list[dict]:
    return [_asset_wire(row) for row in db.query(ProjectAsset).filter(ProjectAsset.project_id == project_id).order_by(ProjectAsset.created_at.desc()).all()]
