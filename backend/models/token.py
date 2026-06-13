from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
from .user import User
from ..ids import generate_cuid

class TokenBase(SQLModel):
    token: str

class TokenCreate(TokenBase):
    user_id: str
    expires: datetime  # Changed from str to datetime to match database tracking
    type: str = "refresh" # Defaulting this to refresh since access tokens aren't saved to DB

# Added table=True so SQLModel maps this to your database!
class Token(SQLModel, table=True):
    __tablename__ = "tokens" # Good practice to name your table explicitly

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    token: str = Field(unique=True, index=True)
    
    # Removed unique=True so a user can be logged in on multiple devices at once
    user_id: str = Field(foreign_key="users.id", ondelete="CASCADE") 
    
    type: str = Field(default="refresh")
    expires: datetime
    
    # Added automated lambda defaults like your User model has
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))