from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field

class Game(SQLModel, table=True):
    __tablename__="games"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    url: str = Field(unique=True)
    date: Optional[str] = None
    repack_number: Optional[str] = None
    version: Optional[str] = None
    cover_image: Optional[str] = None
    genres: Optional[List[str]] = None
    companies: Optional[str] = None
    languages: Optional[str] = None
    original_size: Optional[str] = None
    repack_size: Optional[str] = None
    screenshots: Optional[List[str]] = None
    trailer: Optional[str] = None
    direct_mirrors: Optional[List[str]] = None
    torrent_mirrors: Optional[List[str]] = None
    repack_features: Optional[List[str]] = None
    description: Optional[str] = None
    scraped_at: datetime