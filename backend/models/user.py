from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
from ..ids import generate_cuid

class UserBase(SQLModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class UserLogin(SQLModel):
    email: str
    password: str
    
class UserPublic(UserBase):
    id: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None

class UserUpdate(SQLModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None

class User(SQLModel, table=True):
    id: str = Field(default_factory=generate_cuid, primary_key=True, index=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))