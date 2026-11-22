import re
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class ContactCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    full_name: str = Field(alias="fullName", min_length=2, max_length=150)
    email: str = Field(min_length=3, max_length=320)
    message: str = Field(min_length=10, max_length=4000)

    @field_validator("full_name", "message")
    @classmethod
    def trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field is required")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid email address")
        return value


class ContactReceipt(BaseModel):
    id: uuid.UUID
    status: Literal["accepted"] = "accepted"
