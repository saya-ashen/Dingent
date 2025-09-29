from sqlmodel import Session, select
from dingent.core.db.models import User, UserRole


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
}


def get_user(session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    result = session.exec(statement).first()
    return result


def create_test_user(
    session: Session,
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "testpassword123",
    role: UserRole = UserRole.user,
) -> User:
    """
    创建一个用于测试的用户。

    如果具有相同邮箱的用户已存在，则直接返回该用户。
    否则，创建一个新用户并存入数据库。
    """
    # 1. 检查用户是否已存在
    db_user = get_user(session, email=email)
    if db_user:
        print(f"User with email '{email}' already exists.")
        return db_user

    # 2. 如果用户不存在，则创建新用户
    hashed_password = "$2b$12$DmYECapSrA2wOyBn2xK1sOW4Iqi1T5PtEOZHAyCCE/NmfqvAHTAeG"

    new_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        role=role,
        is_active=True,
    )

    # 3. 将新用户添加到数据库
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    print(f"Successfully created new user '{username}' with email '{email}'.")
    return new_user
