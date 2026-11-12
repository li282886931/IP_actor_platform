from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.database import Base


class Artist(Base):
    __tablename__ = 'artists'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    tags = Column(String(255), default='')
    heat_score = Column(Integer, default=0)
    fan_count = Column(String(64), default='0')
    risk_level = Column(Integer, default=0)
    profile = Column(JSON, default=dict)


class Show(Base):
    __tablename__ = 'shows'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True)
    artist_id = Column(Integer, ForeignKey('artists.id'), nullable=True)
    artist_name = Column(String(255), default='')
    city = Column(String(128), default='')
    date = Column(String(64), default='')
    venue = Column(String(255), default='')
    price = Column(String(64), default='')
    status = Column(String(64), default='on_sale')
    description = Column(Text, default='')
    poster_url = Column(Text, default='')
    artist = relationship('Artist')


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True, index=True)
    show_id = Column(Integer, ForeignKey('shows.id'))
    name = Column(String(255))
    phone = Column(String(64))


class AIGeneration(Base):
    __tablename__ = 'ai_generations'

    id = Column(Integer, primary_key=True, index=True)
    # Legacy records have no verifiable owner and retain NULL ownership.
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    type = Column(String(64), nullable=False)
    prompt = Column(Text, nullable=False)
    result = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())
