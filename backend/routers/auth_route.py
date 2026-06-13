import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from database.db import get_session
from models.user import User, UserCreate, UserLogin
from passlib.context import CryptContext
from ..auth.utils import create_access_token, create_refresh_token, decode_refresh_payload, hash_password, verify_password
from ..models.token import Token, TokenBase, TokenCreate

router = APIRouter(prefix="/auth", tags=["Auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/login")
def login(payload: UserLogin, session: Session = Depends(get_session)):
    statement = select(User).where(User.email == payload.email)
    existing_user = session.exec(statement).first()

    # Clean use of your utility function here:
    if not existing_user or not verify_password(payload.password, existing_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Credentials"
        )
    
    access_token_string = create_access_token(existing_user.id, existing_user.email)
    refresh_token_string, expires_at = create_refresh_token(existing_user.id)

    token_payload = TokenCreate(
        token=refresh_token_string,
        user_id=existing_user.id,
        expires=expires_at,
        type="refresh"
    )

    db_refresh_token = Token.model_validate(token_payload)
    session.add(db_refresh_token)
    session.commit()

    return {
        "access_token": access_token_string,
        "refresh_token": refresh_token_string,
        "token_type": "bearer"
    }
    
@router.post("/register")
def register(payload: UserCreate, session: Session = Depends(get_session)):
    statement = select(User)
    existing_user = session.exec(statement.where(User.email == payload.email)).first()
     
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User already exists"
        )
    
    hashed_password = hash_password(payload.password)

    db_user = User (
        username = payload.username,
        email = payload.email,
        password_hash = hashed_password
    )

    session.add(db_user)
    session.commit()
    session.refresh(db_user)
     

@router.get("/refresh")
def refesh_access_token(payload: TokenBase, session: Session = Depends(get_session)):
    try:
        decode_payload = decode_refresh_payload(payload.token)
        user_id = decode_payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token.")
    
    statement = select(Token).where(Token.token == payload.token)
    db_token = session.exec(statement).first()

    if not db_token:
        raise HTTPException(status_code=401, detail="Token revoked or invalid.")
    
    user = session.get(User, user_id)

    if not user:
        raise HTTPException(status_code=401, detail="User not found.")

    new_access_token = create_access_token(user_id=user.id, email=user.email)

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }

@router.post("/logout")
def logout(payload: TokenBase, session: Session = Depends(get_session)):
    # Look up this token in our DB table
    statement = select(Token).where(Token.token == payload.token)
    db_token = session.exec(statement).first()

    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token invalid or already logged out"
        )

    # Wipe the refresh token out of the database
    session.delete(db_token)
    session.commit()

    return {"message": "Logged out successfully"}