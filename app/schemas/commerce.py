from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ArtistOut(BaseModel):
    id: int
    name: str
    tags: Optional[str]
    heat_score: int
    fan_count: Optional[str]
    risk_level: int
    profile: dict = Field(default_factory=dict)

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
    poster_url: Optional[str] = ''

    model_config = ConfigDict(from_attributes=True)


class AIGenerateIn(BaseModel):
    type: str
    show_name: Optional[str] = ''
    artist: Optional[str] = ''
    city: Optional[str] = ''
    generation_nonce: Optional[str] = ''


class OrderIn(BaseModel):
    name: str
    phone: str
