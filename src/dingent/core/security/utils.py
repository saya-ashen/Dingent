import secrets


def generate_strong_secret(length: int = 32) -> str:
    """生成用于 PBKDF2 的高强度随机密码字符串 (hex格式)"""
    return secrets.token_hex(length)
