import os
import sys
from pathlib import Path

from platformdirs import PlatformDirs

APP_NAME = "dingent"
APP_AUTHOR = "saya"


class AppPaths:
    def __init__(self):
        self._dirs = PlatformDirs(APP_NAME, APP_AUTHOR)

        # 1. 确定 Data 根目录 (优先级: 环境变量 > XDG)
        if env_home := os.getenv("DINGENT_HOME"):
            self.data_root = Path(env_home).resolve()
            # 如果指定了 HOME，Config 和 Log 通常也跟随这个 HOME
            self.config_root = self.data_root / "config"
            self.log_root = self.data_root / "logs"
            self.cache_root = self.data_root / "cache"
        else:
            self.data_root = Path(self._dirs.user_data_dir)
            self.config_root = Path(self._dirs.user_config_dir)
            self.log_root = Path(self._dirs.user_log_dir)
            self.cache_root = Path(self._dirs.user_cache_dir)

        # 2. 运行时资源目录 (存放 Node 和 前端)
        self.runtime_dir = self.cache_root / "runtime"

        # 3. 数据库目录
        self.db_dir = self.data_root / "db"

        # 4. 确保核心目录存在
        for p in [self.data_root, self.config_root, self.log_root, self.runtime_dir, self.db_dir]:
            p.mkdir(parents=True, exist_ok=True)

    @property
    def is_frozen(self) -> bool:
        """是否在 PyInstaller 打包环境中运行"""
        return getattr(sys, "frozen", False)

    @property
    def bundle_dir(self) -> Path:
        """获取打包资源的根目录 (_MEIPASS)"""
        if self.is_frozen:
            return Path(sys._MEIPASS)  # type: ignore
        # 开发模式下，指向项目根目录 (假设 paths.py 在 dingent/core/ 下)
        return Path(__file__).parents[2]

    @property
    def sqlite_path(self) -> Path:
        return self.db_dir / "dingent.sqlite"

    @property
    def env_file(self) -> Path:
        return self.config_root / ".env"

    @property
    def plugins_dir(self) -> Path:
        return self.data_root / "plugins"


paths = AppPaths()
