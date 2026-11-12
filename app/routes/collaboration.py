from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from app.core.responses import json_ok
from app.database import get_db
from app.models import Artist, CollaborationHistory, Notification, Project, Show, ShowProjectBinding
from app.schemas.collaboration import (
    ActionIn, BindingIn, GrantIn, ItemIn, PersonalIn, RequestIn, ReservationIn, ShowUpdateIn,
)
from app.services.auth import resolve_request_context
from app.services import collaboration as service

router = APIRouter(prefix="/collaboration", tags=["角色协作"])


def context(db: Session = Depends(get_db), authorization: str = Header(default=""),
            x_tenant_id: str | None = Header(default=None)):
    return resolve_request_context(db, authorization=authorization, tenant_header=x_tenant_id)


@router.get("")
def overview(ctx=Depends(context), db: Session = Depends(get_db)):
    return json_ok(service.overview(db, ctx))


@router.post("/grants")
def grant(body: GrantIn, ctx=Depends(context), db: Session = Depends(get_db)):
    return json_ok(service.mutate(db, ctx, "grants", body, lambda: service.grant_project(db, ctx, body)))


@router.post("/grants/{grant_id}/revoke")
def revoke(grant_id: int, body: ActionIn, ctx=Depends(context), db: Session = Depends(get_db)):
    return json_ok(service.mutate(db, ctx, f"grants/{grant_id}/revoke", body,
                                 lambda: service.revoke_grant(db, ctx, grant_id, body)))


@router.post("/items")
def create(body: ItemIn, ctx=Depends(context), db: Session = Depends(get_db)):
    return json_ok(service.mutate(db, ctx, "items", body, lambda: service.create_item(db, ctx, body)))


@router.post("/items/{item_id}/actions")
def action(item_id: int, body: ActionIn, ctx=Depends(context), db: Session = Depends(get_db)):
    return json_ok(service.mutate(db, ctx, f"items/{item_id}/actions", body,
                                 lambda: service.act_item(db, ctx, item_id, body)))


@router.get("/items/{item_id}/history")
def item_history(item_id: int, ctx=Depends(context), db: Session = Depends(get_db)):
    service.item_access(db, ctx, item_id)
    return json_ok([service.serialize(h) for h in db.query(CollaborationHistory).filter_by(
        tenant_id=ctx.tenant.id, subject_type="item", subject_id=item_id).order_by(CollaborationHistory.id)])


@router.post("/personal")
def personal(body: PersonalIn, ctx=Depends(context), db: Session = Depends(get_db)):
    return json_ok(service.mutate(db, ctx, "personal", body, lambda: service.personal(db, ctx, body)))


@router.post("/reservations")
def reservation(body: ReservationIn, ctx=Depends(context), db: Session = Depends(get_db)):
    return json_ok(service.mutate(db, ctx, "reservations", body, lambda: service.reservation(db, ctx, body)))


@router.get("/reservations/{order_id}/history")
def reservation_history(order_id: int, ctx=Depends(context), db: Session = Depends(get_db)):
    from app.models import Order
    if not db.query(Order).filter_by(id=order_id, tenant_id=ctx.tenant.id, user_id=ctx.user.id).first():
        service.fail(404, "预约不存在")
    return json_ok([service.serialize(h) for h in db.query(CollaborationHistory).filter_by(
        tenant_id=ctx.tenant.id, subject_type="reservation", subject_id=order_id).order_by(CollaborationHistory.id)])


@router.post("/notifications/{notification_id}/read")
def read_notice(notification_id: int, body: RequestIn, ctx=Depends(context), db: Session = Depends(get_db)):
    def operation():
        from datetime import datetime
        row = db.query(Notification).filter_by(
            id=notification_id, tenant_id=ctx.tenant.id, user_id=ctx.user.id).first()
        if not row:
            service.fail(404, "消息不存在")
        row.status, row.read_at = "read", datetime.utcnow()
        return service.serialize(row)
    return json_ok(service.mutate(db, ctx, f"notifications/{notification_id}/read", body, operation))


@router.post("/artist-binding")
def artist_binding(body: BindingIn, ctx=Depends(context), db: Session = Depends(get_db)):
    def operation():
        if ctx.user.group_code != "root":
            service.fail(403, "仅管理员可维护身份绑定")
        target = service.member(db, ctx, body.user_id)
        if target.group_code != "Artist" or not db.get(Artist, body.artist_id):
            service.fail(422, "请选择有效艺人账号和资料")
        before = {"artist_id": target.artist_id}
        target.artist_id = body.artist_id
        service.history(db, ctx, "binding", target.id, "bind", before, {"artist_id": target.artist_id})
        return {"user_id": target.id, "artist_id": target.artist_id}
    return json_ok(service.mutate(db, ctx, "artist-binding", body, operation))


@router.post("/show-binding")
def show_binding(body: ShowUpdateIn, ctx=Depends(context), db: Session = Depends(get_db)):
    def operation():
        if ctx.user.group_code != "root":
            service.fail(403, "仅管理员可绑定公开演出")
        project = db.query(Project).filter_by(id=body.project_id, tenant_id=ctx.tenant.id).first()
        show = db.get(Show, body.show_id)
        if not project or not show:
            service.fail(404, "项目或演出不存在")
        if project.artist_id != show.artist_id or project.city != show.city:
            service.fail(422, "项目艺人及城市须与公开演出一致")
        row = db.query(ShowProjectBinding).filter_by(show_id=show.id).first()
        if row and (row.tenant_id != ctx.tenant.id or row.project_id != project.id):
            service.fail(409, "演出已绑定其他项目")
        if not row:
            row = ShowProjectBinding(tenant_id=ctx.tenant.id, project_id=project.id, show_id=show.id)
            db.add(row)
            db.flush()
            service.history(db, ctx, "show_binding", row.id, "bind", {}, service.serialize(row))
        return service.serialize(row)
    return json_ok(service.mutate(db, ctx, "show-binding", body, operation))


@router.post("/shows/update")
def show_update(body: ShowUpdateIn, ctx=Depends(context), db: Session = Depends(get_db)):
    return json_ok(service.mutate(db, ctx, "shows/update", body, lambda: service.show_update(db, ctx, body)))
