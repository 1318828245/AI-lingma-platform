from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.template import Template
from app.models.user import User
from app.schemas.template import TemplateOut

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[TemplateOut])
def list_templates(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    templates = (
        db.query(Template).filter(Template.is_active.is_(True)).all()
    )
    result = []
    for tpl in templates:
        item = TemplateOut.model_validate(tpl)
        item.file_count = len(tpl.files_json or {})
        result.append(item)
    return result
