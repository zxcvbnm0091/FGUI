from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import Optional, List
from database.db import get_session
from models.user import User, UserCreate, UserPublic
from passlib.context import CryptContext

router = APIRouter(prefix="/users", tags=["Users"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/", response__model=User)
def create_user(payload: UserCreate, session: Session = Depends(get_session)):
    existing_user = session.exec(select(User).where(User.email == payload.email)).first()

    hashed_password = pwd_context.hash(payload.password)

    if existing_user:
        raise HTTPException(status_code="400", detail="Email already registered")
    
    db_user = User (
        username = payload.username,
        email = payload.email,
        password_hash = hashed_password
    )

    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return db_user

@router.get("/", response_model=List[UserPublic]) 
def list_users(role: Optional[str] = None, session: Session = Depends(get_session)):
    statement = select(User)

    if role is not None:
        statement = statement.where(User.role == role)
    
    statement = statement.order_by(User.created_at.desc())

    return session.exec(statement)

# @router.get("/me", resposne_model=UserPublic)
# def get_user_me(userId: str, session: Session = Depends(get_session)):


    

   
