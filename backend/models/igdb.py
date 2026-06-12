# igdb_game.py
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class IGDBBase(SQLModel):
    title: str


class IGDBPublic(IGDBBase):
    id: int
    cover_url: Optional[str] = None
    release_date: Optional[str] = None
    summary: Optional[str] = None


class IGDBGame(SQLModel, table=True):
    __tablename__ = "igdb_games"

    id: int = Field(primary_key=True)
    title: str = Field(nullable=False, index=True)
    cover_url: Optional[str] = None
    release_date: Optional[str] = None
    summary: Optional[str] = None
    cached_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))