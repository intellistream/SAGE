import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field, field_validator

from sage.common.config.user_paths import get_user_data_dir

# Configuration
# TODO: Move SECRET_KEY to config/env
SECRET_KEY = "sage-studio-secret-key-change-me-in-production"  # pragma: allowlist secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class User(BaseModel):
    id: int
    username: str
    created_at: datetime
    is_guest: bool = False


class UserInDB(User):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    password: str = Field(..., min_length=6)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return v.strip()


class AuthService:
    def __init__(self):
        self.db_path = get_user_data_dir() / "studio.db"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_guest BOOLEAN DEFAULT 0
                )
            """
            )
            conn.commit()

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_user(self, username: str, password: str) -> User:
        hashed_password = self.get_password_hash(password)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, hashed_password, created_at, is_guest) VALUES (?, ?, ?, 0)",
                    (username, hashed_password, datetime.utcnow()),
                )
                user_id = cursor.lastrowid
                conn.commit()

                # Fetch the created user to get the timestamp
                cursor.execute(
                    "SELECT id, username, created_at, is_guest FROM users WHERE id = ?", (user_id,)
                )
                row = cursor.fetchone()
                return User(id=row[0], username=row[1], created_at=row[2], is_guest=bool(row[3]))
        except sqlite3.IntegrityError:
            raise ValueError("Username already registered")

    def create_guest_user(self) -> User:
        import uuid

        username = f"guest_{uuid.uuid4().hex[:8]}"
        password = uuid.uuid4().hex
        hashed_password = self.get_password_hash(password)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, hashed_password, created_at, is_guest) VALUES (?, ?, ?, 1)",
                (username, hashed_password, datetime.utcnow()),
            )
            user_id = cursor.lastrowid
            conn.commit()

            cursor.execute(
                "SELECT id, username, created_at, is_guest FROM users WHERE id = ?", (user_id,)
            )
            row = cursor.fetchone()
            return User(id=row[0], username=row[1], created_at=row[2], is_guest=bool(row[3]))

    def delete_user(self, user_id: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()

    def get_user(self, username: str) -> Optional[UserInDB]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, hashed_password, created_at, is_guest FROM users WHERE username = ?",
                (username,),
            )
            row = cursor.fetchone()
            if row:
                return UserInDB(
                    id=row[0],
                    username=row[1],
                    hashed_password=row[2],
                    created_at=row[3],
                    is_guest=bool(row[4]),
                )
            return None

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[str]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
            return username
        except JWTError:
            return None


# Singleton instance
_auth_service = None


def get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
