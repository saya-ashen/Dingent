import logging

from cryptography.fernet import Fernet, InvalidToken

# --- 常量定义 ---
KEYRING_SERVICE_NAME = "dingent-framework"
KEYRING_PLACEHOLDER_PREFIX = "keyring:"
FALLBACK_MASTER_KEY_FILE = "master.key"
FALLBACK_SECRETS_FILE = "secrets.enc"

logger = logging.getLogger(__name__)


class UserSecretManager:
    """
    一个专注于用户数据加密的管理器。
    使用一个应用级别的主密钥来加密和解密每个用户自己的数据加密密钥(DEK)。
    """

    def __init__(self, master_key: str | bytes):
        """
        使用应用主密钥初始化管理器。

        Args:
            master_key: 应用的主加密密钥，从环境变量或安全存储中获取。
        """
        if isinstance(master_key, str):
            master_key = master_key.encode()

        try:
            self._master_fernet = Fernet(master_key)
            logger.info("UserSecretManager initialized successfully.")
        except (ValueError, TypeError) as e:
            logger.error("Invalid MASTER_KEY provided. It must be a URL-safe base64-encoded 32-byte key.")
            raise ValueError("Invalid MASTER_KEY for UserSecretManager.") from e

    def generate_user_key(self) -> bytes:
        """
        为新用户生成一个新的、原始的数据加密密钥 (DEK)。
        这个密钥本身是明文的，需要被加密后才能存储。

        Returns:
            一个新的 Fernet 密钥（bytes）。
        """
        return Fernet.generate_key()

    def encrypt_user_key(self, user_key: bytes) -> bytes:
        """
        使用应用主密钥加密用户的 DEK，以便安全地存入数据库。

        Args:
            user_key: 用户原始的、明文的 DEK。

        Returns:
            加密后的 DEK (ciphertext)。
        """
        return self._master_fernet.encrypt(user_key)

    def decrypt_user_key(self, encrypted_user_key: bytes) -> bytes:
        """
        使用应用主密钥解密用户的 DEK。

        Args:
            encrypted_user_key: 从数据库中取出的、加密过的用户 DEK。

        Returns:
            用户原始的、明文的 DEK。

        Raises:
            ValueError: 如果解密失败（密钥错误或数据损坏）。
        """
        try:
            return self._master_fernet.decrypt(encrypted_user_key)
        except InvalidToken:
            logger.error("Failed to decrypt user key. The master key may have changed or the data is corrupt.")
            raise ValueError("Decryption failed for user key.")

    def get_user_fernet(self, encrypted_user_key: bytes) -> Fernet:
        """
        【核心便利方法】
        获取一个可用于加密/解密该用户所有数据的 Fernet 实例。

        Args:
            encrypted_user_key: 从数据库中取出的、加密过的用户 DEK。

        Returns:
            一个为该用户初始化的 Fernet 实例。
        """
        decrypted_key = self.decrypt_user_key(encrypted_user_key)
        return Fernet(decrypted_key)
