from app.core.responses import json_ok
from app.database import get_db
from app.models import Artist
from app.models import Evidence
from app.models import Order
from app.models import Project
from app.models import Show
from app.schemas import ArtistOut
from app.schemas import OrderIn
from app.schemas import ShowOut
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional
from urllib.parse import quote


router = APIRouter()


def serialize_order(order: Order, show_title: str = ''):
    return {
        "id": order.id,
        "show_id": order.show_id,
        "show_title": show_title,
        "name": order.name,
        "phone": order.phone,
    }

def is_image_file_url(file_url: str):
    normalized = (file_url or '').split('?', 1)[0].lower()
    return normalized.endswith(('.png', '.jpg', '.jpeg', '.webp'))

def build_ai_show_poster_url(show: Show, image_size: str = 'landscape_4_3'):
    prompt = quote(
        (
            f"Realistic live concert photography for {show.artist_name or show.title}, "
            f"{show.title}, {show.city or 'major city'} {show.venue or 'concert venue'}, "
            "wide stage, audience, professional lighting, premium editorial event poster, no text"
        )
    )
    return f"https://copilot-cn.bytedance.net/api/ide/v1/text_to_image?prompt={prompt}&image_size={image_size}"

def find_uploaded_show_poster_url(db: Session, show: Show):
    project_ids = [
        project_id for (project_id,) in db.query(Project.id)
        .filter(Project.artist_name == (show.artist_name or ''), Project.city == (show.city or ''))
        .all()
    ]
    if not project_ids and show.artist_name:
        project_ids = [
            project_id for (project_id,) in db.query(Project.id)
            .filter(Project.artist_name == show.artist_name)
            .all()
        ]
    if not project_ids:
        return ''
    evidences = (
        db.query(Evidence)
        .filter(Evidence.project_id.in_(project_ids))
        .order_by(Evidence.id.desc())
        .all()
    )
    for evidence in evidences:
        if evidence.evidence_type == 'image' or is_image_file_url(evidence.file_url):
            return evidence.file_url
    return ''

def serialize_show(show: Show, db: Session):
    payload = ShowOut.model_validate(show).model_dump()
    payload["poster_url"] = find_uploaded_show_poster_url(db, show) or show.poster_url or build_ai_show_poster_url(show)
    return payload

def serialize_show_with_recommendation(show: Show, reason: str, score: int, db: Session):
    payload = serialize_show(show, db)
    payload["recommendation_reason"] = reason
    payload["recommendation_score"] = score
    return payload

@router.get('/artists')
def list_artists(q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Artist)
    if q:
        like = f"%{q}%"
        query = query.filter(Artist.name.like(like))
    artists = query.order_by(Artist.heat_score.desc()).all()
    return json_ok([ArtistOut.model_validate(a).model_dump() for a in artists])

@router.get('/artists/{artist_id}')
def get_artist(artist_id: int, db: Session = Depends(get_db)):
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail='Artist not found')
    artist_dict = ArtistOut.model_validate(artist).model_dump()
    heat_score = getattr(artist, 'heat_score', 0) or 0
    if heat_score >= 90:
        cities = ['北京', '上海', '广州']
    elif heat_score >= 80:
        cities = ['北京', '上海']
    elif heat_score >= 60:
        cities = ['省会城市', '一线/新一线']
    else:
        cities = ['本地城市']
    return json_ok({"artist": artist_dict, "city_suggestions": cities})

@router.get('/shows')
def list_shows(city: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Show)
    if city:
        query = query.filter(Show.city == city)
    shows = query.order_by(Show.id.desc()).all()
    return json_ok([serialize_show(show, db) for show in shows])

@router.get('/shows/recommendations')
def recommend_shows(phone: Optional[str] = None, limit: int = 6, db: Session = Depends(get_db)):
    normalized_phone = (phone or '').strip()
    order_counts = dict(
        db.query(Order.show_id, func.count(Order.id))
        .group_by(Order.show_id)
        .all()
    )
    candidate_shows = db.query(Show).filter(Show.status == 'on_sale').all()

    history_orders = []
    history_shows = []
    if normalized_phone:
        history_orders = db.query(Order).filter(Order.phone == normalized_phone).all()
        history_show_ids = [order.show_id for order in history_orders]
        if history_show_ids:
            history_shows = db.query(Show).filter(Show.id.in_(history_show_ids)).all()

    purchased_ids = {show.id for show in history_shows}
    history_artists = {show.artist_name for show in history_shows if show.artist_name}
    history_cities = {show.city for show in history_shows if show.city}
    recommendations = []

    if history_orders:
        for show in candidate_shows:
            if show.id in purchased_ids:
                continue
            score = int(order_counts.get(show.id, 0))
            reasons = []
            if show.artist_name and show.artist_name in history_artists:
                score += 100
                reasons.append(f"你预约过{show.artist_name}相关演出")
            if show.city and show.city in history_cities:
                score += 60
                reasons.append(f"你关注过{show.city}场次")
            if not reasons and order_counts.get(show.id, 0):
                reasons.append("近期预约热度较高")
            if reasons or score > 0:
                recommendations.append((show, reasons[0] if reasons else "近期预约热度较高", score))

    if not recommendations:
        recommendations = [
            (show, "近期预约热度较高", int(order_counts.get(show.id, 0)))
            for show in candidate_shows
        ]

    recommendations.sort(key=lambda item: (item[2], item[0].id), reverse=True)
    return json_ok([
        serialize_show_with_recommendation(show, reason, score, db)
        for show, reason, score in recommendations[:max(1, min(limit, 20))]
    ])

@router.get('/shows/{show_id}')
def get_show(show_id: int, db: Session = Depends(get_db)):
    show = db.query(Show).filter(Show.id == show_id).first()
    if not show:
        raise HTTPException(status_code=404, detail='Show not found')
    return json_ok(serialize_show(show, db))

@router.post('/shows/{show_id}/order')
def order_show(show_id: int, payload: OrderIn, db: Session = Depends(get_db)):
    show = db.query(Show).filter(Show.id == show_id).first()
    if not show:
        raise HTTPException(status_code=404, detail='Show not found')
    order = Order(show_id=show_id, name=payload.name, phone=payload.phone)
    db.add(order)
    db.commit()
    return json_ok({"order_id": order.id, "status": "ok"})
