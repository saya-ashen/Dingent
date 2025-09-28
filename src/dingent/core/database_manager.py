from __future__ import annotations

from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session


class _DatabaseManager:
    """
    Manages a single, shared, synchronous SQLite connection for the entire application.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._engine = None

    def connect(self):
        """
        建立数据库连接。应用启动时调用一次。
        """
        if self._engine is None:
            # 确保父目录存在
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            url = f"sqlite:///{self.db_path}"
            self._engine = create_engine(
                url,
                echo=False,
                future=True,
            )
            # 设置 WAL 模式
            with self._engine.connect() as conn:
                conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
            print(f"Database connection established at {self.db_path}")

    def close(self):
        """
        关闭数据库连接。应用退出时调用。
        """
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            print("Database engine disposed.")

    def get_engine(self):
        """
        返回已初始化的同步引擎。
        """
        if self._engine is None:
            raise RuntimeError("Engine not initialized. Call connect() first.")
        return self._engine

    def get_session(self) -> Session:
        """
        获取一个新的同步会话（调用方负责 with 语句使用）。
        """
        if self._engine is None:
            raise RuntimeError("Engine not initialized. Call connect() first.")
        return Session(self._engine)

    def init_db(self):
        """
        根据 SQLModel 的元数据创建表。需要在所有模型定义完成后调用一次。
        """
        if self._engine is None:
            raise RuntimeError("Engine not initialized. Call connect() first.")
        SQLModel.metadata.create_all(self._engine)
        print("Database schema ensured (create_all).")
