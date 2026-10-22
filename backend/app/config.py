"""Application configuration settings."""
import os
from pydantic import BaseModel


class Settings(BaseModel):
    """Runtime configuration settings."""
    app_name: str = "Warehouse Intelligence Twin API"
    version: str = "1.0.0"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:3000,https://warehouse-intelligence-twin.pages.dev",
        ).split(",")
        if origin.strip()
    ]
    handling_seconds_per_line: float = 10.0
    default_speed_mps: float = 1.2
    max_speed_mps: float = 10.0


settings = Settings()
