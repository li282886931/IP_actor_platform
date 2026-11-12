from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class WebLoginIn(BaseModel):
    account: str
    password: str
    captcha_id: str
    captcha_code: str
    name: Optional[str] = ''


class WechatLoginIn(BaseModel):
    code: str
    phone_code: str
    name: Optional[str] = ''


class UserCreateIn(BaseModel):
    account: str
    name: str
    phone: Optional[str] = ''
    password: str
    group_code: str
    artist_id: Optional[int] = None


class UserUpdateIn(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    group_code: Optional[str] = None
    status: Optional[str] = None
    artist_id: Optional[int] = None
