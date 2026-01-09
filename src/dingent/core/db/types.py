import json
from typing import Any

from sqlalchemy.types import TEXT, TypeDecorator

from dingent.core.secrets import get_secret_manager


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
        return manager.encrypt_string(str(value))

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        """Process value after retrieving from DB (Decrypt)"""
        if value is None:
            return None
        # 将密文解密成明文
        manager = get_secret_manager()
        return manager.decrypt_string(value)


class EncryptedJSON(TypeDecorator):
    """
    自定义类型：
    Python端: dict
    DB端: 加密后的字符串 (TEXT)
    """

    impl = TEXT
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        """
        保存到数据库：Dict -> JSON String -> Encrypted String
        """
        if value is None:
            return None
        # 1. 序列化为 JSON 字符串
        json_str = json.dumps(value, ensure_ascii=False)
        # 2. 加密
        manager = get_secret_manager()
        return manager.encrypt_string(json_str)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        """
        从数据库读取：Encrypted String -> Decrypted String -> Dict
        """
        if value is None:
            return None
        # 1. 解密
        manager = get_secret_manager()
        decrypted_json = manager.decrypt_string(value)

        # 2. 反序列化为 Dict
        if decrypted_json is None:
            return {}
        try:
            return json.loads(decrypted_json)
        except json.JSONDecodeError:
            # 防止数据库数据损坏导致崩库，返回空字典或抛出错误
            return {}
