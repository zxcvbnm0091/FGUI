# wishlist.py
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint
from ..ids import generate_cuid 

class WishlistGame(SQLModel, table=True):
    __tablename__ = "wishlist_items"
    __table_args__ = (UniqueConstraint("user_id", "igdb_game_id"),)

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    user_id: str = Field(foreign_key="users.id", nullable=False, index=True)
    igdb_game_id: int = Field(foreign_key="igdb_games.id", nullable=False, index=True)
    matched_game_id: Optional[int] = Field(default=None, foreign_key="games.id")
    notified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))