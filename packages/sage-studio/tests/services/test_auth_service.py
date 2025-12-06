import os
import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest
from jose import jwt

from sage.studio.services.auth_service import (
    ALGORITHM,
    SECRET_KEY,
    AuthService,
    get_auth_service,
)


@pytest.fixture
def auth_service(tmp_path):
    # Override the db_path for testing
    service = AuthService()
    service.db_path = tmp_path / "test_studio.db"
    service._init_db()
    return service


def test_password_hashing(auth_service):
    password = "testpassword"
    hashed = auth_service.get_password_hash(password)
    assert hashed != password
    assert auth_service.verify_password(password, hashed)
    assert not auth_service.verify_password("wrongpassword", hashed)


def test_create_user(auth_service):
    user = auth_service.create_user("testuser", "password123")
    assert user.username == "testuser"
    assert user.id is not None
    assert user.created_at is not None

    # Test duplicate user
    with pytest.raises(ValueError):
        auth_service.create_user("testuser", "password456")


def test_get_user(auth_service):
    auth_service.create_user("testuser", "password123")
    user = auth_service.get_user("testuser")
    assert user is not None
    assert user.username == "testuser"
    assert user.hashed_password is not None

    user = auth_service.get_user("nonexistent")
    assert user is None


def test_token_creation_and_verification(auth_service):
    data = {"sub": "testuser"}
    token = auth_service.create_access_token(data)
    
    username = auth_service.verify_token(token)
    assert username == "testuser"


def test_token_expiration(auth_service):
    data = {"sub": "testuser"}
    # Create a token that expired 1 minute ago
    token = auth_service.create_access_token(data, expires_delta=timedelta(minutes=-1))
    
    username = auth_service.verify_token(token)
    assert username is None


def test_invalid_token(auth_service):
    username = auth_service.verify_token("invalidtoken")
    assert username is None

def test_short_password():
    from pydantic import ValidationError
    from sage.studio.services.auth_service import UserCreate

    with pytest.raises(ValidationError):
        UserCreate(username="test", password="123")
