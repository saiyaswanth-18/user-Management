import logging
import smtplib
from contextlib import asynccontextmanager
from typing import Annotated

import jwt
import redis
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.mailer import send_otp_email
from app.models import User
from app.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    VerifyRequest,
)
from app.security import (
    create_access_token,
    create_otp,
    hash_otp,
    hash_password,
    read_access_token,
    verify_password,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
bearer_scheme = HTTPBearer(auto_error=False)
PENDING_PREFIX = "registration:"

CREATE_PENDING_SCRIPT = """
if redis.call('EXISTS', KEYS[1]) == 1 then
    return 0
end
redis.call(
    'HSET', KEYS[1],
    'name', ARGV[1],
    'email', ARGV[2],
    'password_hash', ARGV[3],
    'otp_hash', ARGV[4],
    'attempts', 0
)
redis.call('EXPIRE', KEYS[1], ARGV[5])
return 1
"""

VERIFY_OTP_SCRIPT = """
local pending = redis.call('HMGET', KEYS[1], 'name', 'email', 'password_hash', 'otp_hash')
if not pending[4] then
    return {-1}
end
if pending[4] ~= ARGV[1] then
    local attempts = redis.call('HINCRBY', KEYS[1], 'attempts', 1)
    if attempts >= tonumber(ARGV[2]) then
        redis.call('DEL', KEYS[1])
        return {2}
    end
    return {0}
end
redis.call('DEL', KEYS[1])
return {1, pending[1], pending[2], pending[3]}
"""


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    redis_client.ping()
    yield
    redis_client.close()


app = FastAPI(
    title="User Management API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
    lifespan=lifespan,
)


def pending_key(email: str) -> str:
    return f"{PENDING_PREFIX}{email}"


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        is_verified=user.is_verified,
    )


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = read_access_token(credentials.credentials)
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    user = db.get(User, user_id)
    if user is None or not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user


@app.get("/health")
def health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    redis_client.ping()
    return {"status": "ok"}


@app.post("/api/auth/register", status_code=status.HTTP_202_ACCEPTED)
def register(
    request: RegisterRequest, db: Annotated[Session, Depends(get_db)]
) -> dict[str, str]:
    existing_user = db.scalar(select(User).where(User.email == request.email))
    if existing_user:
        raise HTTPException(status_code=409, detail="An account already exists for this email")

    key = pending_key(request.email)
    otp = create_otp()
    created = redis_client.eval(
        CREATE_PENDING_SCRIPT,
        1,
        key,
        request.name,
        request.email,
        hash_password(request.password),
        hash_otp(otp),
        settings.otp_expire_seconds,
    )
    if not int(created):
        raise HTTPException(
            status_code=409,
            detail="A registration is already pending for this email. Verify the latest code.",
        )

    try:
        send_otp_email(request.email, otp)
    except (OSError, smtplib.SMTPException) as exc:
        redis_client.delete(key)
        logger.exception("Could not send verification email to %s", request.email)
        raise HTTPException(
            status_code=503,
            detail="Could not send verification email. Check SMTP configuration and try again.",
        ) from exc

    return {
        "message": "A verification code has been sent to your email.",
        "expires_in_seconds": str(settings.otp_expire_seconds),
    }


@app.post("/api/auth/verify")
def verify_email(
    request: VerifyRequest, db: Annotated[Session, Depends(get_db)]
) -> dict[str, str]:
    result = redis_client.eval(
        VERIFY_OTP_SCRIPT,
        1,
        pending_key(request.email),
        hash_otp(request.otp),
        settings.otp_max_attempts,
    )
    result_status = int(result[0])
    if result_status == -1:
        raise HTTPException(
            status_code=400,
            detail="Verification code expired or no registration is pending. Please register again.",
        )
    if result_status == 0:
        raise HTTPException(status_code=400, detail="Incorrect verification code.")
    if result_status == 2:
        raise HTTPException(
            status_code=400,
            detail="Too many incorrect attempts. Please register again.",
        )

    _, name, email, password_hashed = result
    user = User(name=name, email=email, password_hash=password_hashed, is_verified=True)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.info("Duplicate account encountered while verifying %s", email)
        raise HTTPException(
            status_code=409, detail="An account already exists for this email."
        ) from exc

    return {"message": "Email verified. Your account is ready; you can now log in."}


@app.post("/api/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == request.email))
    if user is None or not user.is_verified or not verify_password(
        request.password, user.password_hash
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return TokenResponse(
        access_token=create_access_token(user.id),
        user=user_response(user),
    )


@app.get("/api/auth/me", response_model=UserResponse)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return user_response(current_user)
