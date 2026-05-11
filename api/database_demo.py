"""Database integration demo — PostgreSQL + MSSQL via SQLAlchemy."""

from kewe import Blueprint, Request, json
from kewe.errors.exceptions import NotFound, BadRequest
from sqlalchemy import create_engine, text, inspect, MetaData, Table, Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import Session
from database_config import POSTGRES_URL, MSSQL_URL

db_bp = Blueprint("database", url_prefix="/api/database")

# Create engines
pg_engine = create_engine(POSTGRES_URL, connect_args={'connect_timeout': 5}, pool_pre_ping=True)
ms_engine = create_engine(MSSQL_URL, connect_args={'timeout': 5}, pool_pre_ping=True)

# Ensure demo table in PostgreSQL
with pg_engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS demo_products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            category VARCHAR(100) DEFAULT 'general',
            in_stock BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.commit()


@db_bp.get("/")
async def db_index():
    return json({
        "databases": {
            "postgresql": "kiwi @ 192.168.18.137:5432",
            "mssql": "BPMDATA_TARGET @ 192.168.18.137",
        },
        "endpoints": {
            "pg_status": "GET /api/database/pg/status",
            "pg_products": "GET /api/database/pg/products",
            "pg_product_create": "POST /api/database/pg/products",
            "pg_product": "GET /api/database/pg/products/{id}",
            "pg_tables": "GET /api/database/pg/tables",
            "ms_status": "GET /api/database/ms/status",
            "ms_tables": "GET /api/database/ms/tables",
        }
    })


# ---- PostgreSQL Endpoints ----
@db_bp.get("/pg/status")
async def pg_status():
    """PostgreSQL connection status."""
    try:
        with pg_engine.connect() as conn:
            result = conn.execute(text("SELECT version(), current_database(), pg_database_size(current_database())"))
            row = result.fetchone()
        return json({
            "status": "connected",
            "version": row[0],
            "database": row[1],
            "size_bytes": row[2],
        })
    except Exception as e:
        return json({"status": "error", "error": str(e)})


@db_bp.get("/pg/tables")
async def pg_tables():
    """List PostgreSQL tables."""
    inspector = inspect(pg_engine)
    tables = []
    for table_name in inspector.get_table_names():
        columns = []
        for col in inspector.get_columns(table_name):
            columns.append({"name": col["name"], "type": str(col["type"]), "nullable": col["nullable"]})
        tables.append({"name": table_name, "columns": columns})
    return json({"tables": tables})


@db_bp.get("/pg/products")
async def pg_products(request: Request):
    """List products from PostgreSQL."""
    page = int(request.query_params.get("page", "1"))
    per_page = int(request.query_params.get("per_page", "10"))
    offset = (page - 1) * per_page

    with pg_engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM demo_products")).scalar()
        rows = conn.execute(
            text("SELECT id, name, price, category, in_stock, created_at FROM demo_products ORDER BY id LIMIT :limit OFFSET :offset"),
            {"limit": per_page, "offset": offset}
        )
        items = []
        for row in rows:
            items.append({
                "id": row[0], "name": row[1], "price": float(row[2]),
                "category": row[3], "in_stock": row[4],
                "created_at": str(row[5]) if row[5] else None,
            })

    return json({"items": items, "total": total, "page": page, "per_page": per_page})


@db_bp.post("/pg/products")
async def pg_create_product(request: Request):
    """Create a product in PostgreSQL."""
    body = await request.json
    name = body.get("name")
    price = body.get("price")
    if not name or not price:
        raise BadRequest("name and price are required")

    with pg_engine.connect() as conn:
        result = conn.execute(
            text("INSERT INTO demo_products (name, price, category, in_stock) VALUES (:name, :price, :category, :in_stock) RETURNING id"),
            {"name": name, "price": float(price), "category": body.get("category", "general"), "in_stock": body.get("in_stock", True)}
        )
        conn.commit()
        new_id = result.scalar()

    return json({"id": new_id, "name": name, "price": float(price), "created": True}, status=201)


@db_bp.get("/pg/products/{product_id:int}")
async def pg_get_product(product_id: int):
    """Get a single product from PostgreSQL."""
    with pg_engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, name, price, category, in_stock, created_at FROM demo_products WHERE id = :id"),
            {"id": product_id}
        ).fetchone()

    if row is None:
        raise NotFound(f"Product {product_id} not found")

    return json({
        "id": row[0], "name": row[1], "price": float(row[2]),
        "category": row[3], "in_stock": row[4],
        "created_at": str(row[5]) if row[5] else None,
    })


# ---- MSSQL Endpoints ----
@db_bp.get("/ms/status")
async def ms_status():
    """MSSQL connection status."""
    try:
        with ms_engine.connect() as conn:
            result = conn.execute(text("SELECT @@VERSION, DB_NAME(), (SELECT SUM(size)*8/1024 FROM sys.database_files)"))
            row = result.fetchone()
        return json({
            "status": "connected",
            "version": row[0].split("\n")[0].strip() if row[0] else "unknown",
            "database": row[1],
            "size_mb": float(row[2]) if row[2] else 0,
        })
    except Exception as e:
        return json({"status": "error", "error": str(e)})


@db_bp.get("/ms/tables")
async def ms_tables():
    """List MSSQL tables."""
    inspector = inspect(ms_engine)
    tables = []
    for table_name in inspector.get_table_names():
        columns = []
        for col in inspector.get_columns(table_name):
            columns.append({"name": col["name"], "type": str(col["type"]), "nullable": col["nullable"]})
        tables.append({"name": table_name, "columns": columns, "row_count": "N/A"})
    return json({"tables": tables})
