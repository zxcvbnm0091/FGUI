from fastapi import Cookie, HTTPException, status, Depends
from sqlmodel import Session, select
from database.db import get_session
from models.user import User

def get_current_user(session_id: str = Cookie(None), session: Session = Depends(get_session)) -> User:
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            details="Not authenticated. Missing session cookie"
        )
    
    user = session.get(User, session_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, details="Invalid session cookie")
    
    return user

def get_current_admin(session_id: str = Cookie(None), session: Session = Depends(get_session)) -> User:
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            details="Not authorized. Missing sesison cookie"
        )
    
    admin = session.get(User, session_id)

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            details="Invalid cookie session"
        )
    
    if admin.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            details="Not authorized"
        )
    
    return admin

