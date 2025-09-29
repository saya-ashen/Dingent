import json
import logging
from pathlib import Path

import keyring
import keyring.errors
from cryptography.fernet import Fernet

# --- 常量定义 ---
KEYRING_SERVICE_NAME = "dingent-framework"
KEYRING_PLACEHOLDER_PREFIX = "keyring:"
FALLBACK_MASTER_KEY_FILE = "master.key"
FALLBACK_SECRETS_FILE = "secrets.enc"

logger = logging.getLogger(__name__)


class SecretManager:
    """
    一个健壮的密钥管理器，自动处理 keyring 的可用性。
    如果 keyring 可用，则使用它。
    如果 keyring 不可用（例如在 WSL/Docker 中），则回退到一个本地加密文件。
    """

    def __init__(self, project_root: Path):
        self._keyring_available = self._check_keyring_availability()
        self._fallback_key = None
        self._fallback_secrets_path = None

        if not self._keyring_available:
            logger.warning("Keyring backend not available. Falling back to encrypted local file for secrets.")
            fallback_dir = project_root / ".secrets"
            self._initialize_fallback(fallback_dir)

    def _check_keyring_availability(self) -> bool:
        """在启动时检查 keyring 后端是否可用。"""
        try:
            # 尝试一个无害的操作来触发后端检查
            keyring.get_password(f"{KEYRING_SERVICE_NAME}-test", "availability-check")
            logger.info("Keyring backend is available.")
            return True
        except keyring.errors.NoKeyringError:
            return False

    def _initialize_fallback(self, fallback_dir: Path):
        """初始化基于加密文件的回退方案。"""
        try:
            fallback_dir.mkdir(parents=True, exist_ok=True)
            # 确保目录权限，仅所有者可访问
            fallback_dir.chmod(0o700)

            master_key_path = fallback_dir / FALLBACK_MASTER_KEY_FILE
            self._fallback_secrets_path = fallback_dir / FALLBACK_SECRETS_FILE

            if not master_key_path.exists():
                logger.info("Generating new master key for fallback secret storage.")
                key = Fernet.generate_key()
                master_key_path.write_bytes(key)
                master_key_path.chmod(0o600)  # 仅所有者可读写

            self._fallback_key = master_key_path.read_bytes()

            if not self._fallback_secrets_path.exists():
                # 如果密钥文件不存在，创建一个空的
                self._write_fallback_secrets({})

        except Exception as e:
            logger.error(f"Failed to initialize fallback secret storage: {e}", exc_info=True)
            # 如果 fallback 也失败了，抛出异常让应用启动失败
            raise RuntimeError("Could not initialize fallback secret storage.") from e

    def _read_fallback_secrets(self) -> dict:
        """读取并解密回退密钥文件。"""
        fernet = Fernet(self._fallback_key)
        encrypted_data = self._fallback_secrets_path.read_bytes()
        decrypted_data = fernet.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode())

    def _write_fallback_secrets(self, secrets: dict):
        """加密并写入回退密钥文件。"""
        fernet = Fernet(self._fallback_key)
        encrypted_data = fernet.encrypt(json.dumps(secrets).encode())
        self._fallback_secrets_path.write_bytes(encrypted_data)
        self._fallback_secrets_path.chmod(0o600)

    def set_secret(self, key_path: str, value: str):
        """根据可用性，将密钥保存到 keyring 或回退文件。"""
        if self._keyring_available:
            keyring.set_password(KEYRING_SERVICE_NAME, key_path, value)
        else:
            secrets = self._read_fallback_secrets()
            secrets[key_path] = value
            self._write_fallback_secrets(secrets)

    def get_secret(self, key_path: str) -> str | None:
        """根据可用性，从 keyring 或回退文件读取密钥。"""
        if self._keyring_available:
            return keyring.get_password(KEYRING_SERVICE_NAME, key_path)
        else:
            secrets = self._read_fallback_secrets()
            return secrets.get(key_path)
