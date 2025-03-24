from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


class URLBase(BaseModel):
    original_url: HttpUrl
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None


class URLCreate(URLBase):
    pass


class URLUpdate(BaseModel):
    original_url: Optional[HttpUrl] = None
    expires_at: Optional[datetime] = None


class URL(URLBase):
    id: int
    short_code: str
    visits: int
    last_visited_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    user_id: Optional[int]

    class Config:
        from_attributes = True


class URLStats(BaseModel):
    original_url: HttpUrl
    short_code: str
    visits: int
    created_at: datetime
    last_visited_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True
