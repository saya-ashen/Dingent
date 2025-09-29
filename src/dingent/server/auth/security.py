from typing import Any


from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

# 1. 密码哈希配置 (Passlib)
#    - schemes=["bcrypt"]: 指定 bcrypt 作为主要的哈希算法。
#    - deprecated="auto": 如果未来更换算法，旧的哈希值仍然可以被验证。
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 2. JWT 配置
#    - SECRET_KEY: 一个用于签名 JWT 的密钥。这必须是保密的！
#      在生产环境中，应从环境变量中加载。
#      可以使用 `openssl rand -hex 32` 命令生成一个安全的密钥。
#    - ALGORITHM: 使用的签名算法。HS256 是对称算法，需要保密密钥。
#    - ACCESS_TOKEN_EXPIRE_MINUTES: Access Token 的有效期。
SECRET_KEY = "YOUR_SUPER_SECRET_KEY_CHANGE_THIS"  # 强烈建议从环境变量读取
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Token 有效期为 30 分钟

# --- 密码相关函数 ---


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码和哈希密码是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码的哈希值"""
    return pwd_context.hash(password)


# --- JWT 相关函数 ---


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    创建 JWT Access Token

    :param data: 要编码到 Token 中的数据 (payload)。
    :param expires_delta: Token 的可选过期时间。
    :return: 编码后的 JWT 字符串。
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any] | None:
    """
    解码 JWT Token，验证其签名和有效期。

    :param token: JWT 字符串。
    :return: 如果 Token 有效，则返回 payload；否则返回 None。
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
