import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from dingent.core.paths import paths
from dingent.core.security.utils import generate_strong_secret  # 导入上面的 paths


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(paths.env_file), env_file_encoding="utf-8", extra="ignore")

    master_key: str = Field(default="", alias="DINGENT_MASTER_KEY")

    @property
    def DINGENT_MASTER_KEY(self) -> str:
        """
        获取 Master Key。如果内存中没有，尝试初始化。
        """
        if not self.master_key:
            # 尝试从文件重新加载（防止首次生成后内存未更新）
            self.master_key = self._load_or_create_key()
        return self.master_key

    def _load_or_create_key(self) -> str:
        """
        核心逻辑：检查文件 -> 读取/生成 -> 返回
        """
        env_path = paths.env_file

        # 1. 尝试从现有的 .env 文件中手动读取 (绕过 Pydantic 缓存)
        if env_path.exists():
            content = env_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                if line.startswith("DINGENT_MASTER_KEY="):
                    return line.split("=", 1)[1].strip()

        # 2. 如果文件里没有，生成新的
        print("[Dingent] 🔐 First run detected. Generating secure master key...")
        new_key = generate_strong_secret()

        # 3. 追加写入 .env
        mode = "a" if env_path.exists() else "w"
        with open(env_path, mode, encoding="utf-8") as f:
            f.write(f"\nDINGENT_MASTER_KEY={new_key}\n")

        # 4. 设置环境变量 (确保当前进程的其他部分也能读到)
        os.environ["DINGENT_MASTER_KEY"] = new_key

        return new_key

    # --- 基础配置 ---
    PROJECT_NAME: str = "dingent"
    ENVIRONMENT: str = "development"

    # 使用 paths 中的路径作为默认值
    DATABASE_URL: str = f"sqlite:///{paths.sqlite_path}"

    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 3000


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
