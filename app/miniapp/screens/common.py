from dataclasses import dataclass, field
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Project, ProjectVersion, User




@dataclass(frozen=True)
class ScreenRequestContext:
    tenant_id: Optional[int] = None
    user_id: Optional[int] = None
    project_id: Optional[int] = None
    version_id: Optional[int] = None
    task_id: Optional[int] = None
    artist_id: Optional[int] = None
    keyword: str = ''


@dataclass(frozen=True)
class ScreenRegistration:
    screen_id: str
    provider_key: str
    domain: str
    required_context: frozenset[str] = field(default_factory=frozenset)


def _screen_context(context: ScreenRequestContext) -> dict:
    return {
        "tenant_id": context.tenant_id,
        "user_id": context.user_id,
        "project_id": context.project_id,
        "version_id": context.version_id,
        "task_id": context.task_id,
        "artist_id": context.artist_id,
    }


def _get_project(db: Session, context: ScreenRequestContext) -> Project:
    project = db.query(Project).filter(
        Project.id == context.project_id,
        Project.tenant_id == context.tenant_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    return project


def _get_current_version(db: Session, project: Project) -> Optional[ProjectVersion]:
    if project.current_version_id:
        return db.query(ProjectVersion).filter(
            ProjectVersion.id == project.current_version_id,
            ProjectVersion.project_id == project.id,
        ).first()
    return None


def _empty_state(title: str, description: str, target_screen: Optional[str] = None) -> dict:
    return {
        "title": title,
        "description": description,
        "action": (
            {"label": "去处理", "target_screen": target_screen}
            if target_screen
            else None
        ),
    }


def _user_names(db: Session, user_ids: set[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    return {
        user.id: user.name
        for user in db.query(User).filter(User.id.in_(user_ids)).all()
    }
