"""The user's own LaTeX resumes, pasted once and reused for every application.

Saving a template reports back which sections were recognised. That feedback is
the point of the endpoint: heading names vary between Overleaf templates, and
finding out that "Relevant Coursework" was never going to be rewritten is much
better here than after generating a resume that looks untouched.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.latex import REWRITABLE, find_sections
from app.db.models import ResumeTemplate
from app.db.session import get_db
from app.schemas import ResumeTemplateIn

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("")
def list_templates(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(ResumeTemplate).order_by(ResumeTemplate.created_at.desc()))
    return [_as_dict(t) for t in rows]


@router.post("", status_code=201)
def create_template(data: ResumeTemplateIn, db: Session = Depends(get_db)) -> dict:
    template = ResumeTemplate(
        name=data.name.strip() or "My resume",
        source=data.source,
        # The first template is the default, or saving one would do nothing.
        is_default=db.scalar(select(ResumeTemplate).limit(1)) is None,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return _as_dict(template)


@router.post("/{template_id}/default")
def set_default(template_id: int, db: Session = Depends(get_db)) -> dict:
    template = _get(db, template_id)
    for other in db.scalars(select(ResumeTemplate).where(ResumeTemplate.is_default.is_(True))):
        other.is_default = False
    template.is_default = True
    db.commit()
    db.refresh(template)
    return _as_dict(template)


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: int, db: Session = Depends(get_db)) -> None:
    template = _get(db, template_id)
    was_default = template.is_default
    db.delete(template)
    db.commit()

    # Deleting the default would otherwise silently drop the whole LaTeX path.
    if was_default:
        replacement = db.scalar(select(ResumeTemplate).order_by(ResumeTemplate.created_at.desc()))
        if replacement is not None:
            replacement.is_default = True
            db.commit()


def _get(db: Session, template_id: int) -> ResumeTemplate:
    template = db.get(ResumeTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="template not found")
    return template


def _as_dict(template: ResumeTemplate) -> dict:
    sections = find_sections(template.source)
    return {
        "id": template.id,
        "name": template.name,
        "is_default": template.is_default,
        "created_at": template.created_at.isoformat(),
        "sections": [
            {"heading": s.heading, "rewritable": s.name in REWRITABLE} for s in sections
        ],
    }
