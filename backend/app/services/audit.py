"""Small, transaction-friendly helper for recording operational actions."""

from app.models.audit import AuditLog


def record_audit(db, *, actor_id: int | None, action: str, target_type: str, target_id: str | int, detail: dict | None = None) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            detail_json=detail,
        )
    )
