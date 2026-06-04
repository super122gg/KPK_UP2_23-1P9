# service.py — Auth Service REST API
#
# Endpoints:
#
# POST   /users/                              — Register new user
# PUT    /users/{user_id}                     — Update user by ID
# DELETE /users/{user_id}                     — Hard-delete user by ID
# GET    /users/{user_id}                     — Get user by ID
# GET    /users/                              — List users (filter: login, is_active)
#
# POST   /auth/login                          — Login, returns JWT access_token
# POST   /auth/reset-password/request         — Request password reset token
# POST   /auth/reset-password/confirm         — Confirm reset with token + new password
#
# POST   /reset-tokens/                       — Create reset token record
# PUT    /reset-tokens/{token_id}             — Update reset token (only is_used field)
# DELETE /reset-tokens/{token_id}             — Hard-delete reset token
# GET    /reset-tokens/{token_id}             — Get reset token by ID
# GET    /reset-tokens/                       — List reset tokens (filter: user_id, is_used)

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime, timedelta
import hashlib
import secrets

from passlib.context import CryptContext
from jose import jwt as _jwt

from models import User, PasswordResetToken, db

# ── Config ────────────────────────────────────────────────────────────────────
SECRET_KEY = "auth_service_secret_change_in_production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return _jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Auth Service", version="1.0.0")


# ══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class UserCreate(BaseModel):
    login: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=6, max_length=255)


class UserUpdate(BaseModel):
    login: Optional[str] = Field(None, min_length=3, max_length=150)
    password: Optional[str] = Field(None, min_length=6, max_length=255)


class UserResponse(BaseModel):
    id: int
    login: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class DeleteResponse(BaseModel):
    success: bool


class LoginRequest(BaseModel):
    login: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=6, max_length=255)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ResetRequestBody(BaseModel):
    login: str = Field(..., min_length=3, max_length=150)


class ResetConfirmBody(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=255)


class ResetTokenCreate(BaseModel):
    user_id: int = Field(..., gt=0)
    token: str = Field(..., max_length=255)
    expires_at: datetime

    @validator("expires_at")
    def expires_at_must_be_future(cls, v: datetime) -> datetime:
        if v <= datetime.utcnow():
            raise ValueError("expires_at must be a future datetime")
        return v


class ResetTokenUpdate(BaseModel):
    # Only is_used is supported for update
    is_used: Optional[bool] = None


class ResetTokenResponse(BaseModel):
    id: int
    user_id: int
    token: str
    expires_at: datetime
    is_used: bool
    created_at: datetime

    class Config:
        orm_mode = True


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _user_to_resp(u: User) -> UserResponse:
    return UserResponse(
        id=u.id,
        login=u.login,
        is_active=u.is_active,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


def _token_to_resp(t: PasswordResetToken) -> ResetTokenResponse:
    # t.__data__["user_id"] returns the raw integer FK value stored by Peewee.
    # This is the standard Peewee approach: ForeignKeyField stores the raw id
    # in __data__ under the field name, avoiding an extra lazy DB query.
    return ResetTokenResponse(
        id=t.id,
        user_id=t.__data__["user_id"],
        token=t.token,
        expires_at=t.expires_at,
        is_used=t.is_used,
        created_at=t.created_at,
    )


# ══════════════════════════════════════════════════════════════════════════════
# USER ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/users/", response_model=UserResponse, status_code=201)
def create_user(data: UserCreate):
    """
    Register a new user.
    Returns the created user (without password hash).
    Example response: {"id": 1, "login": "ivan", "is_active": true, ...}
    """
    if User.select().where(User.login == data.login).exists():
        raise HTTPException(status_code=409, detail="Login already taken")
    now = datetime.utcnow()
    user = User.create(
        login=data.login,
        password_hash=hash_password(data.password),
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    return _user_to_resp(user)


@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, data: UserUpdate):
    """
    Update login and/or password for user by ID.
    Example response: {"id": 1, "login": "new_login", ...}
    """
    try:
        user = User.get_by_id(user_id)
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    if data.login is not None:
        if User.select().where(
            (User.login == data.login) & (User.id != user_id)
        ).exists():
            raise HTTPException(status_code=409, detail="Login already taken")
        user.login = data.login
    if data.password is not None:
        user.password_hash = hash_password(data.password)
    user.updated_at = datetime.utcnow()
    user.save()
    return _user_to_resp(user)


@app.delete("/users/{user_id}", response_model=DeleteResponse)
def delete_user(user_id: int):
    """
    Hard-delete user by ID (Auth Service uses hard delete per requirements).
    Returns {"success": true} if deleted, {"success": false} if not found.
    """
    deleted = User.delete().where(User.id == user_id).execute()
    return DeleteResponse(success=bool(deleted))


@app.get("/users/", response_model=List[UserResponse])
def list_users(
    login: Optional[str] = Query(None, description="Filter by login (partial match)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
):
    """
    Get list of users with optional filters.
    Example: GET /users/?is_active=true&login=ivan
    """
    query = User.select()
    if login is not None:
        query = query.where(User.login.contains(login))
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    return [_user_to_resp(u) for u in query]


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    """
    Get user by ID.
    Example response: {"id": 1, "login": "ivan", "is_active": true, ...}
    """
    try:
        user = User.get_by_id(user_id)
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_resp(user)


# ══════════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/auth/login", response_model=LoginResponse)
def login(data: LoginRequest):
    """
    Login with login/password. Returns JWT access_token.
    Example response: {"access_token": "eyJ...", "token_type": "bearer"}
    """
    try:
        user = User.get(User.login == data.login)
    except User.DoesNotExist:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id), "login": user.login})
    return LoginResponse(access_token=token)


@app.post("/auth/reset-password/request", response_model=ResetTokenResponse)
def reset_password_request(data: ResetRequestBody):
    """
    Request a password reset token for the given login.
    If an active (unused, non-expired) token already exists, returns 409.
    Creates and returns a reset token valid for 1 hour.
    """
    try:
        user = User.get(User.login == data.login)
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

    # Business logic: do not create duplicate active tokens
    active_token_exists = PasswordResetToken.select().where(
        (PasswordResetToken.user_id == user.id) &
        (PasswordResetToken.is_used == False) &
        (PasswordResetToken.expires_at > datetime.utcnow())
    ).exists()
    if active_token_exists:
        raise HTTPException(
            status_code=409,
            detail="An active reset token already exists for this user"
        )

    token_str = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=1)
    rt = PasswordResetToken.create(
        user_id=user.id,
        token=token_str,
        expires_at=expires,
        is_used=False,
        created_at=datetime.utcnow(),
    )
    return _token_to_resp(rt)


@app.post("/auth/reset-password/confirm", response_model=UserResponse)
def reset_password_confirm(data: ResetConfirmBody):
    """
    Confirm password reset using a valid token.
    Marks the token as used and updates the user's password.
    """
    try:
        rt = PasswordResetToken.get(PasswordResetToken.token == data.token)
    except PasswordResetToken.DoesNotExist:
        raise HTTPException(status_code=404, detail="Token not found")
    if rt.is_used:
        raise HTTPException(status_code=400, detail="Token already used")
    if rt.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expired")

    # Explicitly fetch User by raw FK id to avoid Peewee proxy issues
    raw_user_id = rt.__data__["user_id"]
    try:
        user = User.get_by_id(raw_user_id)
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(data.new_password)
    user.updated_at = datetime.utcnow()
    user.save()
    rt.is_used = True
    rt.save()
    return _user_to_resp(user)


# ══════════════════════════════════════════════════════════════════════════════
# RESET TOKEN ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/reset-tokens/", response_model=ResetTokenResponse, status_code=201)
def create_reset_token(data: ResetTokenCreate):
    """
    Create a password reset token record manually.
    expires_at must be a future datetime.
    Example response: {"id": 1, "user_id": 1, "token": "abc...", ...}
    """
    if not User.select().where(User.id == data.user_id).exists():
        raise HTTPException(status_code=404, detail="User not found")
    if PasswordResetToken.select().where(
        PasswordResetToken.token == data.token
    ).exists():
        raise HTTPException(status_code=409, detail="Token already exists")
    rt = PasswordResetToken.create(
        user_id=data.user_id,
        token=data.token,
        expires_at=data.expires_at,
        is_used=False,
        created_at=datetime.utcnow(),
    )
    return _token_to_resp(rt)


@app.put("/reset-tokens/{token_id}", response_model=ResetTokenResponse)
def update_reset_token(token_id: int, data: ResetTokenUpdate):
    """
    Update reset token. Only the is_used field is supported for update.
    Example response: {"id": 1, "is_used": true, ...}
    """
    try:
        rt = PasswordResetToken.get_by_id(token_id)
    except PasswordResetToken.DoesNotExist:
        raise HTTPException(status_code=404, detail="Token not found")
    if data.is_used is not None:
        rt.is_used = data.is_used
    rt.save()
    return _token_to_resp(rt)


@app.delete("/reset-tokens/{token_id}", response_model=DeleteResponse)
def delete_reset_token(token_id: int):
    """
    Hard-delete reset token by ID.
    Returns {"success": true} if deleted.
    """
    deleted = PasswordResetToken.delete().where(
        PasswordResetToken.id == token_id
    ).execute()
    return DeleteResponse(success=bool(deleted))


@app.get("/reset-tokens/", response_model=List[ResetTokenResponse])
def list_reset_tokens(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    is_used: Optional[bool] = Query(None, description="Filter by used status"),
):
    """
    Get list of reset tokens with optional filters.
    Example: GET /reset-tokens/?user_id=1&is_used=false
    """
    query = PasswordResetToken.select()
    if user_id is not None:
        query = query.where(PasswordResetToken.user_id == user_id)
    if is_used is not None:
        query = query.where(PasswordResetToken.is_used == is_used)
    return [_token_to_resp(t) for t in query]


@app.get("/reset-tokens/{token_id}", response_model=ResetTokenResponse)
def get_reset_token(token_id: int):
    """
    Get reset token by ID.
    Example response: {"id": 1, "user_id": 1, "token": "abc...", ...}
    """
    try:
        rt = PasswordResetToken.get_by_id(token_id)
    except PasswordResetToken.DoesNotExist:
        raise HTTPException(status_code=404, detail="Token not found")
    return _token_to_resp(rt)