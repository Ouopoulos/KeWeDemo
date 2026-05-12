"""Database and Redis connection configuration."""

# MSSQL
MSSQL_URL = (
    "mssql+pyodbc://sa:123123.@127.0.0.1/dat"
    "?driver=ODBC+Driver+17+for+SQL+Server"
)

# PostgreSQL
POSTGRES_URL = "postgresql+psycopg://postgres:123123.@127.0.0.1:5432/kewe"

# Redis
REDIS_CONFIG = {
    "host": "127.0.0.1",
    "port": 6379,
    "password": "123123.",
}

REDIS_URL = f"redis://:{REDIS_CONFIG['password']}@{REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}/0"

# Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
