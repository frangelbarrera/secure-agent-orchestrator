import hashlib
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Literal

import anyio
import bcrypt
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.crud_users import crud_users
from .config import settings
from .db.crud_token_blacklist import crud_token_blacklist
from .schemas import TokenBlacklistCreate, TokenData

SECRET_KEY: SecretStr = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# bcrypt truncates passwords at 72 bytes silently. We pre-hash with SHA-256
# (deterministic, fixed 32-byte output) so any-length passwords are protected
# against silent truncation without losing bcrypt's adaptive cost property.
_BCRYPT_MAX_BYTES = 72

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


def _prehash_password(password: str) -> bytes:
    """Pre-hash a password with SHA-256 before passing it to bcrypt.

    bcrypt silently truncates inputs longer than 72 bytes. Pre-hashing with
    SHA-256 yields a fixed 32-byte digest (encoded as hex) that always fits
    within bcrypt's limit, while preserving bcrypt's adaptive cost.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest().encode("utf-8")


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Run bcrypt in the default thread pool so it does not block the event loop.
    # A single bcrypt.checkpw call at cost=12 takes ~250ms, which is enough to
    # stall an async worker under modest login concurrency.
    def _check() -> bool:
        try:
            return bcrypt.checkpw(_prehash_password(plain_password), hashed_password.encode())
        except (ValueError, TypeError):
            return False

    return await anyio.to_thread.run_sync(_check)


def get_password_hash(password: str) -> str:
    """Hash a password synchronously. Intended to be wrapped in a thread.

    Kept synchronous because the CRUD layer currently calls it inline; once
    that call site is made async, prefer the async helper below.
    """
    hashed_password: str = bcrypt.hashpw(_prehash_password(password), bcrypt.gensalt()).decode()
    return hashed_password


async def get_password_hash_async(password: str) -> str:
    return await anyio.to_thread.run_sync(get_password_hash, password)


async def authenticate_user(username_or_email: str, password: str, db: AsyncSession) -> dict[str, Any] | Literal[False]:
    if "@" in username_or_email:
        db_user = await crud_users.get(db=db, email=username_or_email, is_deleted=False)
    else:
        db_user = await crud_users.get(db=db, username=username_or_email, is_deleted=False)

    # Constant-time-ish: always run bcrypt even when the user does not exist,
    # so the response time does not leak whether the username is registered.
    # We hash a dummy password so the bcrypt cost is paid either way.
    if not db_user:
        await verify_password(password, "$2b$12$" + "0" * 53)
        return False

    if not await verify_password(password, db_user["hashed_password"]):
        return False

    return db_user


async def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta if expires_delta is not None else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "token_type": TokenType.ACCESS})
    encoded_jwt: str = jwt.encode(to_encode, SECRET_KEY.get_secret_value(), algorithm=ALGORITHM)
    return encoded_jwt


async def create_refresh_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta if expires_delta is not None else timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "token_type": TokenType.REFRESH})
    encoded_jwt: str = jwt.encode(to_encode, SECRET_KEY.get_secret_value(), algorithm=ALGORITHM)
    return encoded_jwt


async def verify_token(token: str, expected_token_type: TokenType, db: AsyncSession) -> TokenData | None:
    """Verify a JWT and return TokenData if valid.

    Checks, in order:
      1. The token is not in the database-backed blacklist.
      2. The signature is valid (jose raises JWTError on tampering).
      3. The 'exp' claim is in the future.
      4. The 'token_type' claim matches the expected type (access vs refresh).
    """
    is_blacklisted = await crud_token_blacklist.exists(db, token=token)
    if is_blacklisted:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM])
        username_or_email: str | None = payload.get("sub")
        token_type: str | None = payload.get("token_type")

        if username_or_email is None or token_type != expected_token_type:
            return None

        return TokenData(username_or_email=username_or_email)

    except JWTError:
        return None


async def blacklist_tokens(access_token: str, refresh_token: str, db: AsyncSession) -> None:
    """Blacklist both access and refresh tokens until their natural expiry.

    Tokens whose signature cannot be decoded (already expired, tampered, or
    signed with a different key) are silently skipped: there is nothing to
    blacklist because they will already be rejected by verify_token.
    """
    for token in (access_token, refresh_token):
        await blacklist_token(token, db)


async def blacklist_token(token: str, db: AsyncSession) -> None:
    try:
        payload = jwt.decode(token, SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM])
    except JWTError:
        # Token is already invalid; nothing to blacklist.
        return

    exp_timestamp = payload.get("exp")
    if exp_timestamp is None:
        return

    expires_at = datetime.fromtimestamp(int(exp_timestamp), tz=UTC)
    await crud_token_blacklist.create(db, object=TokenBlacklistCreate(token=token, expires_at=expires_at))
