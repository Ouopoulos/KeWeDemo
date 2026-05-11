"""Class-based views demo blueprint.

Uses HTTPMethodView internally for demonstration, but registers
individual route handlers that dispatch to the view class methods
for proper path parameter injection.
"""

from kewe import Blueprint, Request, json
from kewe.routing.views import HTTPMethodView
from kewe.errors.exceptions import NotFound
from models.schemas import products_db, Product

views_bp = Blueprint("views", url_prefix="/api/views")


class ProductView(HTTPMethodView):
    """Class-based view for product CRUD — used internally, with
    registered handlers that delegate to this view."""

    @staticmethod
    async def list_get(request: Request):
        return json([{
            "id": p.id, "name": p.name, "price": p.price,
            "category": p.category, "view_type": "class-based",
        } for p in products_db.values()])

    @staticmethod
    async def list_post(request: Request):
        body = await request.json
        new_id = max(products_db.keys(), default=0) + 1
        product = Product(
            id=new_id, name=body["name"],
            price=float(body["price"]),
            category=body.get("category", "general"),
        )
        products_db[new_id] = product
        return json({
            "id": product.id, "name": product.name,
            "price": product.price, "view_type": "class-based",
        }, status=201)

    @staticmethod
    async def detail_get(request: Request, product_id: int):
        product = products_db.get(product_id)
        if product is None:
            raise NotFound(f"Product {product_id} not found")
        return json({
            "id": product.id, "name": product.name,
            "price": product.price, "category": product.category,
            "in_stock": product.in_stock, "view_type": "class-based",
        })

    @staticmethod
    async def detail_put(request: Request, product_id: int):
        product = products_db.get(product_id)
        if product is None:
            raise NotFound(f"Product {product_id} not found")
        body = await request.json
        if "name" in body:
            product.name = body["name"]
        if "price" in body:
            product.price = float(body["price"])
        if "category" in body:
            product.category = body["category"]
        return json({
            "id": product.id, "name": product.name,
            "price": product.price, "view_type": "class-based",
        })

    @staticmethod
    async def detail_delete(request: Request, product_id: int):
        if product_id not in products_db:
            raise NotFound(f"Product {product_id} not found")
        del products_db[product_id]
        return json({"message": f"Product {product_id} deleted", "view_type": "class-based"})


# Register routes that delegate to ProductView static methods
views_bp.get("/products")(ProductView.list_get)
views_bp.post("/products")(ProductView.list_post)
views_bp.get("/products/{product_id:int}")(ProductView.detail_get)
views_bp.put("/products/{product_id:int}")(ProductView.detail_put)
views_bp.delete("/products/{product_id:int}")(ProductView.detail_delete)
