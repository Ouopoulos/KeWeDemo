"""Products blueprint with query params and pagination."""

from kewe import Blueprint, Request, json, Query
from kewe.errors.exceptions import NotFound
from models.schemas import products_db

products_bp = Blueprint("products", url_prefix="/api/products")


@products_bp.get("/")
async def list_products(
    category: str = Query(default=""),
    min_price: float = Query(default=0),
    in_stock_only: bool = Query(default=False),
    page: int = Query(default=1),
    per_page: int = Query(default=10),
):
    products = list(products_db.values())

    if category:
        products = [p for p in products if p.category == category]
    if in_stock_only:
        products = [p for p in products if p.in_stock]
    products = [p for p in products if p.price >= min_price]

    total = len(products)
    start = (page - 1) * per_page
    page_items = products[start:start + per_page]

    return json({
        "items": [{"id": p.id, "name": p.name, "price": p.price, "category": p.category, "in_stock": p.in_stock} for p in page_items],
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@products_bp.get("/{product_id:int}")
async def get_product(product_id: int):
    product = products_db.get(product_id)
    if product is None:
        raise NotFound(f"Product {product_id} not found")
    return json({"id": product.id, "name": product.name, "price": product.price, "category": product.category})


@products_bp.post("/")
async def create_product(request: Request):
    body = await request.json
    new_id = max(products_db.keys(), default=0) + 1
    from models.schemas import Product
    product = Product(
        id=new_id,
        name=body["name"],
        price=float(body["price"]),
        category=body.get("category", "general"),
    )
    products_db[new_id] = product
    return json({"id": product.id, "name": product.name, "price": product.price}, status=201)
