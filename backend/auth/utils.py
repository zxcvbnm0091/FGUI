import  jwt
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlmodel import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, List
from ..core.config import settings
from ..services.user import get_user_by_email
from ..models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def authenticate_user(session: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(session, email)
    
    if not user:
        return None
        
    is_password_correct = verify_password(password, user.password_hash)
    if not is_password_correct:
        return None
    
    return user

def create_access_token(user_id: str, email: str, ) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire
    }

    encode_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return encode_jwt

def create_refresh_token(user_id: str) -> tuple[str, datetime]:
    expires_at  = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": user_id,
        "exp": expires_at
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return token, expires_at

def decode_refresh_payload(refresh_token: str) ->List[dict]:
    return jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])