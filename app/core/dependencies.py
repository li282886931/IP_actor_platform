from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import RequestContext, get_or_create_default_context, resolve_request_context


def project_write_context(
    db: Session = Depends(get_db),
    authorization: str = Header(default=""),
    x_tenant_id: str = Header(default=""),
) -> RequestContext:
    """Respect supplied sessions; preserve the legacy headerless API context."""
    if authorization or x_tenant_id:
        return resolve_request_context(db, authorization=authorization, tenant_header=x_tenant_id)
    tenant, user = get_or_create_default_context(db)
    return RequestContext(tenant=tenant, user=user)
