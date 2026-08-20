from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.models.message import Message
from app.models.modification import Modification
from app.schemas.version import ProjectVersionDiffOut, ProjectVersionOut, RollbackOut
from app.services.project import get_owned_project
from app.services.version import get_version, list_versions, previous_version, rollback_project, version_diff, version_manifest

router = APIRouter(prefix="/api/projects/{project_id}/versions", tags=["versions"])


def _version_out(version) -> ProjectVersionOut:
    return ProjectVersionOut(
        id=version.id,
        project_id=version.project_id,
        version_no=version.version_no,
        source_type=version.source_type,
        source_id=version.source_id,
        summary=version.summary,
        file_count=len(version_manifest(version)),
        created_at=version.created_at,
    )


def _record_modification_review(db: Session, version, review_status: str) -> None:
    if version.source_type != "modification" or version.source_id is None:
        return
    modification = db.get(Modification, version.source_id)
    if modification is None or modification.project_id != version.project_id:
        return
    diff = dict(modification.diff_json or {})
    diff["review_status"] = review_status
    diff["version_id"] = version.id
    modification.diff_json = diff
    db.add(Message(
        session_id=modification.session_id,
        role="assistant",
        content=review_status,
        msg_type="modification_review",
        tool_call_json={"version_id": version.id, "status": review_status},
    ))


@router.get("", response_model=list[ProjectVersionOut])
def project_versions(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_owned_project(db, project_id, user.id)
    return [_version_out(version) for version in list_versions(db, project_id)]


@router.get("/{version_id}/diff", response_model=ProjectVersionDiffOut)
def project_version_diff(project_id: int, version_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_owned_project(db, project_id, user.id)
    version = get_version(db, project_id, version_id)
    return ProjectVersionDiffOut(
        version_id=version.id,
        version_no=version.version_no,
        files=version_diff(db, project_id, version),
    )


@router.post("/{version_id}/rollback", response_model=RollbackOut)
def project_version_rollback(project_id: int, version_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_owned_project(db, project_id, user.id)
    version = get_version(db, project_id, version_id)
    restored_files = rollback_project(db, project_id, version)
    return RollbackOut(version=_version_out(version), restored_files=restored_files)


@router.post("/{version_id}/undo", response_model=RollbackOut)
def project_version_undo(project_id: int, version_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_owned_project(db, project_id, user.id)
    version = get_version(db, project_id, version_id)
    previous = previous_version(db, project_id, version)
    restored_files = rollback_project(db, project_id, previous)
    _record_modification_review(db, version, "undone")
    db.commit()
    return RollbackOut(version=_version_out(previous), restored_files=restored_files)


@router.post("/{version_id}/accept")
def project_version_accept(project_id: int, version_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_owned_project(db, project_id, user.id)
    version = get_version(db, project_id, version_id)
    if version.source_type != "modification":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Only modification results can be accepted")
    _record_modification_review(db, version, "accepted")
    db.commit()
    return {"ok": True, "status": "accepted", "version_id": version.id}
