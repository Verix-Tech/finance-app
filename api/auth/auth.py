from os import getenv
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote_plus

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.future import select

from database_manager.connector import DatabaseManager
from database_manager.models.models import User


# Security configuration
def _get_secret_key() -> str:
    """Read database password from file specified in environment variable."""
    secret_key_file = getenv("SECRET_KEY")
    try:
        if not secret_key_file:
            raise ValueError("SECRET_KEY environment variable is not set")
        with open(secret_key_file, encoding="utf-8") as file:
            return quote_plus(str(file.read()))
    except FileNotFoundError:
        raise ValueError(f"Secret key file not found: {secret_key_file}")
    except IOError as e:
        raise ValueError(f"Failed to read password file: {secret_key_file}") from e


SECRET_KEY = _get_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Database setup
db_manager = DatabaseManager()


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserCreate(UserBase):
    password: str


class UserInDB(UserBase):
    hashed_password: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY is not set")
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user(username: str) -> Optional[UserInDB]:
    if not isinstance(username, str):
        return None
    with db_manager.get_session() as session:
        result = session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user:
            return UserInDB(
                username=str(user.username),
                email=str(user.email) if user.email is not None else None,
                full_name=str(user.full_name) if user.full_name is not None else None,
                disabled=bool(user.disabled) if user.disabled is not None else None,
                hashed_password=str(user.hashed_password),
            )
        return None


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY is not set")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not isinstance(username, str):
            raise credentials_exception
        token_data = TokenData(username=username)
        if not token_data.username:
            raise credentials_exception
        user = get_user(username=token_data.username)
        if user is None:
            raise credentials_exception
        return user
    except JWTError:
        raise credentials_exception


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def create_user(user_data: UserCreate) -> UserInDB:
    with db_manager.get_session() as session:
        # Check if user already exists
        existing_user = session.execute(
            select(User).where(User.username == user_data.username)
        ).scalar_one_or_none()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already registered")

        # Create new user
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            disabled=False,
        )
        session.add(db_user)
        session.commit()
        session.refresh(db_user)

        return UserInDB(
            username=str(db_user.username),
            email=str(db_user.email) if db_user.email is not None else None,
            full_name=str(db_user.full_name) if db_user.full_name is not None else None,
            disabled=bool(db_user.disabled) if db_user.disabled is not None else None,
            hashed_password=str(db_user.hashed_password),
        )
