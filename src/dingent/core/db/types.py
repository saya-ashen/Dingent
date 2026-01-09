import json
from typing import Any

from sqlalchemy.types import TEXT, TypeDecorator

from dingent.core.security.crypto import get_secret_manager


class EncryptedString(TypeDecorator):
    """
    自定义 SQLAlchemy 类型。
    - 写入数据库前：自动调用 encrypt
    - 从数据库读出后：自动调用 decrypt
    """

    impl = TEXT  # 在数据库中作为 TEXT 类型存储
    cache_ok = True  # 允许 SQLAlchemy 缓存此类型

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        """Process value before inserting into DB (Encrypt)"""
        if value is None:
            return None
        # 将明文加密成密文
        manager = get_secret_manager()
        return manager.encrypt(str(value))

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        """Process value after retrieving from DB (Decrypt)"""
        if value is None:
            return None
        # 将密文解密成明文
        manager = get_secret_manager()
        return manager.decrypt(value)


class EncryptedJSON(TypeDecorator):
    """
    Python端: dict
    DB端: 加密后的字符串 (TEXT)
    """

    impl = TEXT
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        # Dict -> JSON Str -> Encrypt
        json_str = json.dumps(value, ensure_ascii=False)
        return get_secret_manager().encrypt(json_str)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return {}
        # Decrypt -> JSON Str -> Dict
        decrypted = get_secret_manager().decrypt(value)
        if decrypted is None:
            return {}
        try:
            return json.loads(decrypted)
        except json.JSONDecodeError:
            return {}
