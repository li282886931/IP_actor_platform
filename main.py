from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, MetaData, ForeignKey, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
import os
import requests

DB_FILE = os.path.join(os.path.dirname(__file__), 'demo.db')
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_FILE}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# --- ORM models ---
class Artist(Base):
    __tablename__ = 'artists'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    tags = Column(String, default='')
    heat_score = Column(Integer, default=0)   # 0-100
    fan_count = Column(String, default='0')   # e.g. '500万'
    risk_level = Column(Integer, default=0)   # 0-5

class Show(Base):
    __tablename__ = 'shows'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    artist_id = Column(Integer, ForeignKey('artists.id'), nullable=True)
    artist_name = Column(String, default='')
    city = Column(String, default='')
    date = Column(String, default='')
    venue = Column(String, default='')
    price = Column(String, default='')  # e.g. '380-1280'
    status = Column(String, default='on_sale')
    description = Column(Text, default='')
    artist = relationship('Artist')

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, index=True)
    show_id = Column(Integer, ForeignKey('shows.id'))
    name = Column(String)
    phone = Column(String)

class AIGeneration(Base):
    __tablename__ = 'ai_generations'
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)
    prompt = Column(Text, nullable=False)
    result = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())

# --- Pydantic schemas ---
class ArtistOut(BaseModel):
    id: int
    name: str
    tags: Optional[str]
    heat_score: int
    fan_count: Optional[str]
    risk_level: int

    model_config = ConfigDict(from_attributes=True)

class ShowOut(BaseModel):
    id: int
    title: str
    artist_id: Optional[int]
    artist_name: Optional[str]
    city: Optional[str]
    date: Optional[str]
    venue: Optional[str]
    price: Optional[str]
    status: Optional[str]
    description: Optional[str]

    model_config = ConfigDict(from_attributes=True)

class AIGenerateIn(BaseModel):
    type: str
    show_name: Optional[str] = ''
    artist: Optional[str] = ''
    city: Optional[str] = ''

class OrderIn(BaseModel):
    name: str
    phone: str

# --- App init ---
app = FastAPI(title='锐音场 Demo Backend')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Helpers ---
def json_ok(data):
    return {"code": 0, "data": data, "message": "ok"}

# --- Create DB and seed data if needed ---
def init_db():
    if not os.path.exists(DB_FILE):
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            # Seed artists (fan_count as text, risk_level as integer 0-5)
            a1 = Artist(name='周杰伦', tags='流行/华语', heat_score=95, fan_count='5000万', risk_level=0)
            a2 = Artist(name='五月天', tags='摇滚/台湾', heat_score=88, fan_count='2000万', risk_level=0)
            a3 = Artist(name='林俊杰', tags='流行/R&B', heat_score=82, fan_count='1500万', risk_level=2)
            db.add_all([a1, a2, a3])
            db.commit()

            # Seed shows (price as text, include date and status)
            s1 = Show(title='周杰伦·北京演唱会', artist_id=a1.id, artist_name=a1.name, city='北京', date='2026-09-10', venue='鸟巢', price='380-1280', status='on_sale', description='周杰伦个人巡回演唱会 — 北京站')
            s2 = Show(title='五月天·上海演唱会', artist_id=a2.id, artist_name=a2.name, city='上海', date='2026-12-31', venue='梅赛德斯-奔驰文化中心', price='480-1280', status='on_sale', description='五月天跨年演唱会 — 上海站')
            s3 = Show(title='林俊杰小巨蛋特别场', artist_id=a3.id, artist_name=a3.name, city='台北', date='2026-10-05', venue='台北小巨蛋', price='420-980', status='on_sale', description='林俊杰抒情特别场')
            db.add_all([s1, s2, s3])
            db.commit()
        finally:
            db.close()
    else:
        # Ensure tables exist (in case file exists but empty schema)
        Base.metadata.create_all(bind=engine)

init_db()

# --- API endpoints ---
@app.get('/artists')
def list_artists(q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Artist)
    if q:
        like = f"%{q}%"
        query = query.filter(Artist.name.like(like))
    artists = query.order_by(Artist.heat_score.desc()).all()
    return json_ok([ArtistOut.from_orm(a).dict() for a in artists])

@app.get('/artists/{artist_id}')
def get_artist(artist_id: int, db: Session = Depends(get_db)):
    a = db.query(Artist).filter(Artist.id == artist_id).first()
    if not a:
        raise HTTPException(status_code=404, detail='Artist not found')
    artist_dict = ArtistOut.from_orm(a).dict()
    # Simulate city matching suggestions based on heat_score
    hs = getattr(a, 'heat_score', 0) or 0
    if hs >= 90:
        cities = ['北京','上海','广州']
    elif hs >= 80:
        cities = ['北京','上海']
    elif hs >= 60:
        cities = ['省会城市','一线/新一线']
    else:
        cities = ['本地城市']
    return json_ok({"artist": artist_dict, "city_suggestions": cities})

@app.post('/ai/generate')
def ai_generate(payload: AIGenerateIn, db: Session = Depends(get_db)):
    # Build prompt
    prompt = f"""
    你是演出行业营销专家。请为以下演出生成{payload.type}：
    演出：{payload.show_name}，艺人：{payload.artist}，城市：{payload.city}
    要求：年轻化、有传播力、带emoji、不超过150字。
    """.strip()

    api_key = os.getenv('DASHSCOPE_API_KEY') or os.getenv('DASHSCOPE_API_TOKEN')
    result_text = None

    if api_key:
        try:
            resp = requests.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "qwen-turbo", "input": {"messages": [{"role": "user", "content": prompt}]}}
            )
            resp.raise_for_status()
            j = resp.json()
            # Attempt to extract text safely
            result_text = j.get('output', {}).get('text') if isinstance(j, dict) else None
            if not result_text:
                # fallback common path
                result_text = j.get('data', [{}])[0].get('content', '') if isinstance(j, dict) else None
        except Exception as e:
            print('AI API error:', e)
            result_text = None

    if not result_text:
        # Fallback mock
        if payload.type == 'poster':
            result_text = f"🎵 {payload.show_name} · {payload.artist} · {payload.city} —— 不容错过的现场，立即抢票！🔥"
        elif payload.type == 'video_script':
            result_text = f"短视频脚本：开场s1 展示{payload.artist}，过渡s2 展示现场，结尾s3 呼吁到场。"
        else:
            result_text = f"生成：{payload.type} for {payload.show_name} by {payload.artist} in {payload.city}"

    # Save generation record
    try:
        gen = AIGeneration(type=payload.type, prompt=prompt, result=result_text)
        db.add(gen)
        db.commit()
    except Exception as e:
        print('Failed to save AI generation:', e)

    return json_ok({"result": result_text})

@app.get('/shows')
def list_shows(city: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Show)
    if city:
        q = q.filter(Show.city == city)
    shows = q.order_by(Show.id.desc()).all()
    return json_ok([ShowOut.from_orm(s).dict() for s in shows])

@app.get('/shows/{show_id}')
def get_show(show_id: int, db: Session = Depends(get_db)):
    s = db.query(Show).filter(Show.id == show_id).first()
    if not s:
        raise HTTPException(status_code=404, detail='Show not found')
    return json_ok(ShowOut.from_orm(s).dict())

@app.post('/shows/{show_id}/order')
def order_show(show_id: int, payload: OrderIn, db: Session = Depends(get_db)):
    s = db.query(Show).filter(Show.id == show_id).first()
    if not s:
        raise HTTPException(status_code=404, detail='Show not found')
    order = Order(show_id=show_id, name=payload.name, phone=payload.phone)
    db.add(order)
    db.commit()
    return json_ok({"order_id": order.id, "status": "ok"})

# Health
@app.get('/ping')
def ping():
    return {'ok': True}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=False)
