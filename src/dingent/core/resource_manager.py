import pickle
import sqlite3
import uuid
from pathlib import Path

from loguru import logger

from .log_manager import log_with_context
from .types import ToolResult


class ResourceManager:
    """
    使用 SQLite 存储 ToolResult（工具完整输出）的持久化资源管理器。
    当达到最大容量时，会根据时间戳移除最旧的资源 (FIFO)。
    """

    def __init__(self, store_path: str | Path, max_size: int = 100):
        if not isinstance(max_size, int) or max_size <= 0:
            raise ValueError("max_size must be a positive integer.")

        self.db_path = Path(store_path)
        self.max_size = max_size

        # Ensure the directory for the database exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # `check_same_thread=False` is important for use in multi-threaded
        # applications like web servers (e.g., FastAPI).
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._initialize_db()
        logger.info(f"SqliteResourceManager initialized with DB at '{self.db_path}' and a maximum capacity of {self.max_size} resources.")

    def _initialize_db(self):
        """Create the resources table if it doesn't exist."""
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS resources (
                    id TEXT PRIMARY KEY,
                    data BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def register(self, resource: ToolResult) -> str:
        """
        序列化并存储一个新的资源，如果超出容量，则删除最旧的资源。
        """
        # 1. Check current size and enforce max_size (FIFO)
        if len(self) >= self.max_size:
            with self._conn:
                cursor = self._conn.cursor()
                # Find the oldest resource ID
                cursor.execute("SELECT id FROM resources ORDER BY created_at ASC LIMIT 1")
                oldest_id_tuple = cursor.fetchone()
                if oldest_id_tuple:
                    oldest_id = oldest_id_tuple[0]
                    # Delete the oldest resource
                    cursor.execute("DELETE FROM resources WHERE id = ?", (oldest_id,))
                    logger.warning(f"Capacity reached. Removing oldest resource with ID: {oldest_id}")

        # 2. Serialize the resource object and insert it
        new_id = str(uuid.uuid4())
        serialized_resource = pickle.dumps(resource)  # Use pickle to serialize the object

        with self._conn:
            self._conn.execute("INSERT INTO resources (id, data) VALUES (?, ?)", (new_id, serialized_resource))

        current_size = len(self)
        log_with_context(
            "info",
            "ToolResult registered to SQLite",
            context={
                "resource_id": new_id,
                "payload_count": len(resource.display),
                "has_data": resource.data is not None,
                "total_resources": current_size,
                "capacity_used_percent": round((current_size / self.max_size) * 100, 2),
            },
            correlation_id=f"toolres_{new_id[:8]}",
        )
        return new_id

    def get(self, resource_id: str) -> ToolResult | None:
        """通过 ID 从数据库中检索并反序列化资源。"""
        cursor = self._conn.cursor()
        cursor.execute("SELECT data FROM resources WHERE id = ?", (resource_id,))
        row = cursor.fetchone()

        if not row:
            logger.warning(f"Resource with ID '{resource_id}' not found in the database.")
            return None

        # Deserialize the object from BLOB data using pickle
        return pickle.loads(row[0])

    def get_model_text(self, resource_id: str) -> str | None:
        """获取资源的 model_text 字段。"""
        resource = self.get(resource_id)
        return resource.model_text if resource else None

    def clear(self) -> None:
        """从数据库中删除所有资源。"""
        with self._conn:
            self._conn.execute("DELETE FROM resources")
        logger.info("All resources have been cleared from the SQLite database.")

    def close(self) -> None:
        """关闭数据库连接。"""
        self._conn.close()
        logger.info("SQLiteResourceManager database connection closed.")

    def __len__(self) -> int:
        """返回数据库中当前存储的资源数量。"""
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(id) FROM resources")
        return cursor.fetchone()[0]

    def __repr__(self) -> str:
        return f"<SqliteResourceManager(db='{self.db_path}', current_size={len(self)}, max_size={self.max_size})>"
