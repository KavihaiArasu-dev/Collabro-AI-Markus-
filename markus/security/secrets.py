"""
Markus AI — Secrets Manager

Encrypted storage for API keys and sensitive configuration.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

from config.settings import settings

logger = logging.getLogger(__name__)


class SecretsManager:
    """
    Manages encrypted secrets (API keys, tokens, etc.).

    Uses Fernet symmetric encryption. The encryption key is derived
    from the MARKUS_SECRET_KEY environment variable.
    """

    def __init__(self):
        self._secrets: dict[str, str] = {}
        self._secrets_file = Path(settings.base_dir) / "data" / ".secrets.enc"
        self._fernet = self._init_fernet()
        self._load_secrets()
        logger.info("Secrets Manager initialized")

    def _init_fernet(self) -> Optional[Fernet]:
        """Initialize Fernet encryption from the secret key."""
        try:
            # Derive a valid Fernet key from the secret key
            import hashlib
            import base64
            key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            return Fernet(fernet_key)
        except Exception as e:
            logger.warning(f"Failed to initialize encryption: {e}")
            return None

    def set_secret(self, key: str, value: str):
        """Store a secret."""
        self._secrets[key] = value
        self._save_secrets()
        logger.info(f"Secret stored: {key}")

    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret."""
        return self._secrets.get(key)

    def delete_secret(self, key: str):
        """Delete a secret."""
        if key in self._secrets:
            del self._secrets[key]
            self._save_secrets()
            logger.info(f"Secret deleted: {key}")

    def list_keys(self) -> list[str]:
        """List all secret keys (not values)."""
        return list(self._secrets.keys())

    def _save_secrets(self):
        """Save secrets to encrypted file."""
        if not self._fernet:
            return

        try:
            self._secrets_file.parent.mkdir(parents=True, exist_ok=True)
            data = json.dumps(self._secrets).encode()
            encrypted = self._fernet.encrypt(data)
            self._secrets_file.write_bytes(encrypted)
        except Exception as e:
            logger.error(f"Failed to save secrets: {e}")

    def _load_secrets(self):
        """Load secrets from encrypted file."""
        if not self._fernet or not self._secrets_file.exists():
            return

        try:
            encrypted = self._secrets_file.read_bytes()
            data = self._fernet.decrypt(encrypted)
            self._secrets = json.loads(data.decode())
            logger.info(f"Loaded {len(self._secrets)} secrets")
        except Exception as e:
            logger.warning(f"Failed to load secrets: {e}")
            self._secrets = {}


# Singleton
secrets_manager = SecretsManager()
