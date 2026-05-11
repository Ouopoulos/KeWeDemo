"""Demo configuration"""

from dataclasses import dataclass

from kewe import KeweConfig


@dataclass
class AppConfig(KeweConfig):
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8080
    secret_key: str = "demo-secret-key-change-in-production-32ch"


config = AppConfig()
