import base64
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import SecretStr

logger = logging.getLogger(__name__)


class UserSecretManager:
    def __init__(self, master_key: SecretStr):
        """
        Initialize with a master key (SecretStr).
        """
        if not master_key or not master_key.get_secret_value():
            raise ValueError("Master key cannot be empty")

        # In a production multi-tenant system, this salt should ideally be unique per user
        # or stored in the DB config, but a static salt is acceptable for a self-hosted app
        # as long as the master_key is unique per installation.
        salt = b"dingent_static_salt_v1"

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480_000,
        )

        # Derive the Fernet key
        key_bytes = kdf.derive(master_key.get_secret_value().encode())
        self._fernet = Fernet(base64.urlsafe_b64encode(key_bytes))

    def encrypt_string(self, text: str | None) -> str | None:
        """Encrypt plain text -> Base64 String (for DB storage)"""
        if not text:
            return None
        try:
            # Fernet returns bytes, decode to str for SQLModel Text field
            return self._fernet.encrypt(text.encode()).decode("utf-8")
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt_string(self, ciphertext: str | None) -> str | None:
        """Decrypt Base64 String -> Plain text"""
        if not ciphertext:
            return None
        try:
            if isinstance(ciphertext, str):
                ciphertext = ciphertext.encode("utf-8")
            return self._fernet.decrypt(ciphertext).decode("utf-8")
        except InvalidToken:
            logger.error("Decryption failed: Invalid Token. Master Key might have changed.")
            return None


@lru_cache
def get_secret_manager() -> UserSecretManager:
    """Dependency to get the singleton instance."""
    from dingent.core.config import settings

    if not settings.DINGENT_MASTER_KEY:
        raise RuntimeError("DINGENT_MASTER_KEY is missing in settings/env")

    return UserSecretManager(settings.DINGENT_MASTER_KEY)
