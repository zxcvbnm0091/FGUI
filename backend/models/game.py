from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field

class Game(SQLModel):
    id: int = Field(primary_key=True)
    title: str
    url: str = Field(unique=True)
    date: Optional[str] = None
    repack_number: Optional[str] = None
    version: Optional[str] = None
    cover_image: Optional[str] = None
    genres: Optional[str] = None
    companies: Optional[str] = None
    language: Optional[str] = None
    original_size: Optional[str] = None
    repack_size: Optional[str] = None
    screenshots: Optional[str] = None
    trailer: Optional[str] = None
    direct_mirrors: Optional[str] = None
    torrent_mirrors: Optional[str] = None
    repack_features: Optional[str] = None
    description: Optional[str] = None
    scrape_at: datetime