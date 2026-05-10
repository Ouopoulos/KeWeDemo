"""Data models for the demo — pure Python dataclasses (no Pydantic needed)."""

from dataclasses import dataclass, field
from typing import Optional


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
