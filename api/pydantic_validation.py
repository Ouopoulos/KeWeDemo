"""Pydantic validation demo blueprint."""

from kewe import Blueprint, Request, json, Body
from kewe.errors.exceptions import BadRequest, NotFound
from pydantic import ValidationError
from models.schemas import (
    UserCreateModel, UserUpdateModel, ProductCreateModel,
    users_db, products_db, User, Product,
)

pydantic_bp = Blueprint("pydantic", url_prefix="/api/pydantic")


def handle_validation(model_class, data: dict):
    """Validate data against a Pydantic model, raise BadRequest on failure."""
    try:
        return model_class(**data)
    except ValidationError as e:
        errors = []
        for err in e.errors():
            errors.append({"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"]})
        raise BadRequest({"validation_errors": errors})


@pydantic_bp.post("/users")
async def create_user_validated(request: Request):
    """Create a user with Pydantic validation."""
    body = await request.json
    model = handle_validation(UserCreateModel, body)

    new_id = max(users_db.keys(), default=0) + 1
    user = User(id=new_id, username=model.username, email=model.email, role=model.role)
    users_db[new_id] = user
    return json({"id": user.id, "username": user.username, "email": user.email, "role": user.role}, status=201)


@pydantic_bp.put("/users/{user_id:int}")
async def update_user_validated(user_id: int, request: Request):
    """Update a user with Pydantic validation."""
    user = users_db.get(user_id)
    if user is None:
        raise NotFound(f"User {user_id} not found")

    body = await request.json
    model = handle_validation(UserUpdateModel, body)

    changed = False
    if model.username is not None:
        user.username = model.username
        changed = True
    if model.email is not None:
        user.email = model.email
        changed = True
    if model.role is not None:
        user.role = model.role
        changed = True
    if model.active is not None:
        user.active = model.active
        changed = True

    if not changed:
        raise BadRequest("No valid fields to update")

    return json({"id": user.id, "username": user.username, "email": user.email, "role": user.role})


@pydantic_bp.post("/products")
async def create_product_validated(request: Request):
    """Create a product with Pydantic validation."""
    body = await request.json
    model = handle_validation(ProductCreateModel, body)

    new_id = max(products_db.keys(), default=0) + 1
    product = Product(
        id=new_id,
        name=model.name,
        price=model.price,
        category=model.category,
        in_stock=model.in_stock,
    )
    products_db[new_id] = product
    return json({
        "id": product.id, "name": product.name,
        "price": product.price, "category": product.category,
        "in_stock": product.in_stock,
        "validated_with": "pydantic",
    }, status=201)
