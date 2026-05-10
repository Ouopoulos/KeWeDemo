"""Demo configuration"""

from kewe import KeweConfig


class AppConfig(KeweConfig):
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    secret_key: str = "demo-secret-key-change-in-production-32ch"


config = AppConfig()
