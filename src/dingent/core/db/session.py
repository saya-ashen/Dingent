from pathlib import Path

from sqlalchemy import create_engine, event
from sqlmodel import Session, SQLModel, select

from .models import *  # noqa: F403
from .models import Role

# --- 1. Configuration ---
DB_PATH = Path(".dingent/data/dingent.db").resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_PATH}"

# --- 2. Engine Creation ---
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    # connect_args={"check_same_thread": False},  # 如确实需要跨线程复用连接再开启
)


def _set_sqlite_pragmas(dbapi_connection, connection_record):
    print(connection_record)
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


event.listen(engine, "connect", _set_sqlite_pragmas)


def create_initial_roles():
    """检查并创建默认角色"""
    with Session(engine) as session:
        # 定义你系统需要的默认角色
        required_roles = ["admin", "user", "guest"]

        for role_name in required_roles:
            # 查询该角色是否存在
            statement = select(Role).where(Role.name == role_name)
            results = session.exec(statement)
            role = results.first()

            # 如果不存在，则创建
            if not role:
                print(f"正在创建默认角色: {role_name}")
                new_role = Role(name=role_name, description=f"系统默认 {role_name} 角色")
                session.add(new_role)

        session.commit()


# --- 3. Database Initialization Function ---
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    create_initial_roles()


create_db_and_tables()
