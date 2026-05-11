"""Data models for the demo — pure Python dataclasses + Pydantic models for validation."""

from dataclasses import dataclass, field
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, field_validator


# ---- Dataclass Models (used by in-memory DB) ----
@dataclass
class User:
    id: int
    username: str
    email: str
    role: str = "user"
    active: bool = True


@dataclass
class Product:
    id: int
    name: str
    price: float
    category: str
    in_stock: bool = True


@dataclass
class LoginRequest:
    username: str
    password: str


@dataclass
class TokenResponse:
    access_token: str
    token_type: str = "bearer"


@dataclass
class TaskResult:
    task_id: str
    status: str
    message: str


# ---- Pydantic Validation Models ----
class UserCreateModel(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    email: str = Field(min_length=5, max_length=100)
    role: str = Field(default="user", pattern=r"^(admin|moderator|user|guest)$")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v


class UserUpdateModel(BaseModel):
    username: Optional[str] = Field(default=None, min_length=2, max_length=50)
    email: Optional[str] = Field(default=None, min_length=5, max_length=100)
    role: Optional[str] = Field(default=None, pattern=r"^(admin|moderator|user|guest)$")
    active: Optional[bool] = None


class ProductCreateModel(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)
    category: str = Field(default="general", min_length=1, max_length=50)
    in_stock: bool = True


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    per_page: int


# In-memory "databases"
users_db: dict[int, User] = {
    1: User(id=1, username="admin", email="admin@kewe.dev", role="admin"),
    2: User(id=2, username="alice", email="alice@kewe.dev", role="user"),
    3: User(id=3, username="bob", email="bob@kewe.dev", role="user"),
}

products_db: dict[int, Product] = {
    1: Product(id=1, name="Widget Pro", price=29.99, category="tools"),
    2: Product(id=2, name="Gadget X", price=49.99, category="electronics"),
    3: Product(id=3, name="SuperGlue 5000", price=9.99, category="supplies"),
}

# File upload storage
uploads_store: dict[str, dict] = {}
