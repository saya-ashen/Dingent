from ..auth.security import verify_password

PROD_FAKE_USERS_DB = {
    "user@example.com": {
        "id": "user_123",
        "email": "user@example.com",
        "username": "user_123",
        "full_name": "Regular User",
        "hashed_password": "$2b$12$DmYECapSrA2wOyBn2xK1sOW4Iqi1T5PtEOZHAyCCE/NmfqvAHTAeG",
        "role": "user",
    },
    "admin@example.com": {
        "id": "admin_456",
        "email": "admin@example.com",
        "username": "admin_456",
        "full_name": "Admin User",
        "hashed_password": "$2b$12$DmYECapSrA2wOyBn2xK1sOW4Iqi1T5PtEOZHAyCCE/NmfqvAHTAeG",
        "role": "admin",
    },
}


def get_user(db, username: str):
    """Get user from fake database."""
    if username in db:
        user_dict = db[username]
        return user_dict
    return None


def authenticate_user(username: str, password: str):
    """
    生产级别的用户认证函数
    1. 从数据库获取用户
    2. 验证密码哈希
    """
    user = get_user(PROD_FAKE_USERS_DB, username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user
