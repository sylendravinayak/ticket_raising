import uuid
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime


class SignupRequest(BaseModel):
    """Request body for user registration."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!"
            }
        }
    )


class LoginRequest(BaseModel):
    """Request body for user login."""

    email: EmailStr
    password: str
    device_id: str = Field(
        min_length=1,
        max_length=255,
        description="Unique device identifier for session tracking",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
                "device_id": "chrome-macbook-abc123",
            }
        }
    )


class RefreshRequest(BaseModel):
    """Request body for token refresh."""

    refresh_token: str
    device_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "device_id": "chrome-macbook-abc123",
            }
        }
    )


class LogoutRequest(BaseModel):
    """Request body for logout."""

    refresh_token: str


class TokenResponse(BaseModel):
    """Token pair returned on login/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token TTL in seconds")


class UserResponse(BaseModel):
    """Public user data — never includes password."""

    id: uuid.UUID
    email: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SignupResponse(BaseModel):
    """Response after successful registration."""

    user: UserResponse
    message: str = "Account created. Please verify your email."