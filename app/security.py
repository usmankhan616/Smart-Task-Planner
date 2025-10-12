import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from .database import engine
from .models import User

# WARNING: SECRET_KEY is generated on each startup for this prototype.
# In a real application, this should be a fixed secret stored securely.
SECRET_KEY = os.urandom(32).hex()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# PROTOTYPE ONLY: Plain text password verification. NOT FOR PRODUCTION.
def verify_password(plain_password, stored_password):
    return plain_password == stored_password

# PROTOTYPE ONLY: Password is not hashed. NOT FOR PRODUCTION.
def get_password_hash(password):
    return password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(request: Request) -> Optional[User]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    # The token from the cookie includes "Bearer ", so we strip it
    token = token.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None
    
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
    
    if user is None:
        return None
    return user

