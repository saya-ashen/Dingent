from pathlib import Path

from sqlalchemy import create_engine, event
from sqlmodel import SQLModel

from .models import *

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
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


event.listen(engine, "connect", _set_sqlite_pragmas)


# --- 3. Database Initialization Function ---
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


create_db_and_tables()
