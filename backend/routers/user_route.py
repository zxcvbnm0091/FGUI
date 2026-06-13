from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlmodel import Session, select
from typing import Optional, List
from database.db import get_session
from models.user import User, UserCreate, UserPublic, UserUpdate
from passlib.context import CryptContext
from dependencies.auth import get_current_user, get_current_admin

router = APIRouter(prefix="/users", tags=["Users"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# CREATE USER
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

# GET ALL USERS (ADMIN)
@router.get("/", response_model=List[UserPublic]) 
def list_users(role: Optional[str] = None, current_admin: User = Depends(get_current_admin), session: Session = Depends(get_session)):
    
    if not current_admin:
        raise  HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            details="Not authorized"
        )
    
    statement = select(User)

    if role is not None:
        statement = statement.where(User.role == role)
    
    statement = statement.order_by(User.created_at.desc())

    return session.exec(statement)

# GET USER BY ID (ADMIN)
@router.get("/{user_id}", response_model=UserPublic)
def get_user_by_id(user_id: str, current_admin: User = Depends(get_current_admin), session: Session = Depends(get_session)):
    
    if not current_admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, details="Not Authorized")
    
    user = session.get(User, user_id)

    return user

# GET USER DATA (USER)
@router.get("/me", response_model="UserPublic")
def get_user_me(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if not  current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            details="Not authorized"
        )
    
    user = session.get(User, current_user.id)

    return user

# UPDATE USER DATA (USER) 
@router.patch("/me", response_model="UserPublic")
def update_user_me(payload: UserUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    user = session.get(User, current_user.id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User not found"
        )
    
    update_data = payload.model_dump(exclude_unset=True)

    for key,value in update_data.items():
        setattr(user, key, value)

    session.add(user)
    session.commit()
    session.refresh(user)

    return user

# UPDATE USER DATA (ADMIN)
@router.patch("/admin/users/{user_id}", response_model=UserPublic)
def admin_update_any_user(user_id: str, payload: UserUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            details="Not authorized"
        )
    
    target_user = session.get(User, id)

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            details="User not found"
        )

    update_data = payload.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(target_user, key, value)

    session.add(target_user)
    session.commit()
    session.refresh(target_user)

    return target_user

# DELETE USER DATA
@router.delete("/", status_code=204)
def delete_user(response: Response, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    session.delete(current_user)
    session.commit()

    response.delete_cookie(key="session_token")

    return None    

