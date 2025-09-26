PROD_FAKE_USERS_DB = {
    "user@example.com": {
        "id": "user_123",
        "email": "user@example.com",
        "username": "user_123",
        "full_name": "Regular User",
        # testpassword123
        "hashed_password": "$2b$12$DmYECapSrA2wOyBn2xK1sOW4Iqi1T5PtEOZHAyCCE/NmfqvAHTAeG",
        "role": ["user"],
    },
    "admin@example.com": {
        "id": "admin_456",
        "email": "admin@example.com",
        "username": "admin_456",
        "full_name": "Admin User",
        "hashed_password": "$2b$12$DmYECapSrA2wOyBn2xK1sOW4Iqi1T5PtEOZHAyCCE/NmfqvAHTAeG",
        "role": ["admin"],
    },
}


def get_user(username: str):
    """Get user from fake database."""
    if username in PROD_FAKE_USERS_DB:
        user_dict = PROD_FAKE_USERS_DB[username]
        return user_dict
    return None
