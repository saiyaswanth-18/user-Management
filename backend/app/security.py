import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from secrets import randbelow
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.config import settings


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_otp() -> str:
    return f"{randbelow(1_000_000):06d}"


def hash_otp(otp: str) -> str:
    return hmac.new(
        settings.jwt_secret.encode(), otp.encode(), hashlib.sha256
    ).hexdigest()


def create_access_token(user_id: UUID) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_expire_minutes
    )
    return jwt.encode(
        {"sub": str(user_id), "exp": expires_at},
        settings.jwt_secret,
        algorithm="HS256",
    )


def read_access_token(token: str) -> UUID:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    return UUID(payload["sub"])
