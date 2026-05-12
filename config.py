"""Demo configuration with extended settings."""

from dataclasses import dataclass

from kewe import KeweConfig


@dataclass
class AppConfig(KeweConfig):
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8080
    secret_key: str = "demo-secret-key-change-in-production-32ch"

    # Rate limiting defaults
    rate_limit_enabled: bool = True
    rate_limit_max: int = 100
    rate_limit_period: int = 60

    # CSRF
    csrf_secret: str = "demo-csrf-secret-key-32-chars!"
    csrf_enabled: bool = True

    # Cache
    cache_backend: str = "memory"
    cache_default_ttl: int = 300

    # Circuit breaker
    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 3
    circuit_breaker_timeout: float = 10.0


config = AppConfig()
