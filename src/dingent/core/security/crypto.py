import os
from functools import lru_cache
from cryptography.fernet import Fernet, InvalidToken
from loguru import logger
from dingent.core.paths import paths
from dingent.core.config import settings  # 引入配置


class UserSecretManager:
    def __init__(self):
        # 初始化时直接获取密钥
        self._key = self._load_or_create_key()
        try:
            self._fernet = Fernet(self._key)
        except ValueError:
            logger.critical("Invalid Master Key format! Please check your env or key file.")
            raise

    def _load_or_create_key(self) -> bytes:
        """
        优先级: 1. 环境变量 (Docker/CI)  2. 本地文件 (Desktop/Dev)  3. 自动生成
        """
        # 1. 检查 Settings (即环境变量)
        if settings.DING_MASTER_KEY:
            return settings.DING_MASTER_KEY.encode("utf-8")

        # 2. 检查本地数据目录文件
        key_file = paths.data_root / "security" / "master.key"

        if key_file.exists():
            return key_file.read_bytes().strip()

        # 3. 都没有，生成新的并保存 (Zero-Config 核心)
        logger.info(f"✨ Generating new security master key at: {key_file}")
        key_file.parent.mkdir(parents=True, exist_ok=True)

        new_key = Fernet.generate_key()
        key_file.write_bytes(new_key)

        # 设置文件权限 (仅当前用户读写)
        if os.name == "posix":
            key_file.chmod(0o600)

        return new_key

    def encrypt(self, data: str | None) -> str | None:
        if data is None:
            return None
        return self._fernet.encrypt(data.encode()).decode()

    def decrypt(self, token: str | None) -> str | None:
        if token is None:
            return None
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken:
            logger.error("Decryption failed: Invalid Token. Did the master key change?")
            return None


@lru_cache
def get_secret_manager() -> UserSecretManager:
    return UserSecretManager()
