"""
Markus AI — Configuration Settings

Centralized configuration loaded from environment variables with sensible defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class OmniRouteSettings(BaseSettings):
    """OmniRoute AI Gateway connection settings."""
    base_url: str = Field(default="http://localhost:20128/v1", alias="OMNIROUTE_BASE_URL")
    api_key: str = Field(default="", alias="OMNIROUTE_API_KEY")
    timeout: int = 120
    max_retries: int = 3


class DatabaseSettings(BaseSettings):
    """Database connection settings."""
    url: str = Field(
        default="mysql+pymysql://kavi:mvkagagb.@localhost:3306/markus",
        alias="DATABASE_URL",
    )
    host: str = Field(default="localhost", alias="MYSQL_HOST")
    port: int = Field(default=3306, alias="MYSQL_PORT")
    username: str = Field(default="kavi", alias="MYSQL_USERNAME")
    password: str = Field(default="mvkagagb.", alias="MYSQL_PASSWORD")
    dbname: str = Field(default="markus", alias="MYSQL_DBNAME")
    echo: bool = False


class MemorySettings(BaseSettings):
    """Memory system settings."""
    db_path: str = Field(default="./data/memory.db", alias="MEMORY_DB_PATH")


class RAGSettings(BaseSettings):
    """RAG / Embeddings settings."""
    embedding_model: str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")
    vector_store_path: str = Field(default="./data/vector_store", alias="VECTOR_STORE_PATH")
    documents_path: str = Field(default="./data/documents", alias="DOCUMENTS_PATH")
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 5


class Settings(BaseSettings):
    """Root settings — aggregates all sub-settings."""
    # Application
    host: str = Field(default="0.0.0.0", alias="MARKUS_HOST")
    port: int = Field(default=8000, alias="MARKUS_PORT")
    env: str = Field(default="development", alias="MARKUS_ENV")
    debug: bool = Field(default=True, alias="MARKUS_DEBUG")
    secret_key: str = Field(default="change-this-to-a-random-secret-key", alias="MARKUS_SECRET_KEY")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="./logs/markus.log", alias="LOG_FILE")

    # Sub-settings
    omniroute: OmniRouteSettings = OmniRouteSettings()
    database: DatabaseSettings = DatabaseSettings()
    memory: MemorySettings = MemorySettings()
    rag: RAGSettings = RAGSettings()

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_development(self) -> bool:
        return self.env == "development"

    @property
    def is_production(self) -> bool:
        return self.env == "production"


# Singleton instance
settings = Settings()
