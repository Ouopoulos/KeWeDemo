"""Database and Redis connection configuration."""

# MSSQL
MSSQL_URL = (
    "mssql+pyodbc://sa:nm123123.@192.168.18.137/BPMDATA_TARGET"
    "?driver=ODBC+Driver+17+for+SQL+Server"
)

# PostgreSQL
POSTGRES_URL = "postgresql+psycopg://postgres:nm123123.@192.168.18.137:5432/kiwi"

# Redis
REDIS_CONFIG = {
    "host": "192.168.18.137",
    "port": 6379,
    "password": "nm123123.",
}

REDIS_URL = f"redis://:{REDIS_CONFIG['password']}@{REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}/0"

# Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
