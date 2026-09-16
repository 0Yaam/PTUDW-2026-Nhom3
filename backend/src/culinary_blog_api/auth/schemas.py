import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
USER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


class RegisterRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    full_name: str = Field(alias="fullName", min_length=1, max_length=150)
    email: str = Field(min_length=3, max_length=320)
    user_name: str = Field(alias="userName", min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Full name is required")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid email address")
        return value

    @field_validator("user_name")
    @classmethod
    def validate_user_name(cls, value: str) -> str:
        value = value.strip()
        if not USER_NAME_PATTERN.fullmatch(value):
            raise ValueError("User name may contain only letters, numbers, and underscores")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not all(
            (
                re.search(r"[A-Z]", value),
                re.search(r"[a-z]", value),
                re.search(r"\d", value),
                re.search(r"[^A-Za-z0-9]", value),
            )
        ):
            raise ValueError(
                "Password must include uppercase, lowercase, number, and special character"
            )
        return value


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid email address")
        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    full_name: str = Field(alias="fullName")
    email: str
    user_name: str = Field(alias="userName")
    avatar_url: str | None = Field(alias="avatarUrl")
    roles: list[str]


class AuthResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(alias="accessToken")
    refresh_token: str = Field(alias="refreshToken")
    expires_at: datetime = Field(alias="expiresAt")
    user: UserRead
