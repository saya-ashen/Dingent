import hashlib
import os
import shutil
import sys
import tarfile
from pathlib import Path

from rich import print

from dingent.core.paths import paths  # 修改导入源


class AssetManager:
    def __init__(self):
        self.target_dir = paths.runtime_dir  # 使用 paths
        self.version_file = self.target_dir / "version.hash"
        self.source_tar = paths.bundle_dir / "runtime.tar.gz"  # 使用 paths

    def ensure_assets(self):
        """确保运行时环境是最新的"""
        # 如果不是打包环境，直接返回开发路径
        if not paths.is_frozen:
            return self._get_dev_paths()

        if not self.source_tar.exists():
            print(f"[bold red]❌ Critical Error: Runtime assets not found at {self.source_tar}![/bold red]")
            sys.exit(1)

        current_hash = self._get_file_hash(self.source_tar)

        if self._needs_update(current_hash):
            self._extract_assets(current_hash)

        return self._get_prod_paths()

    def _get_file_hash(self, path: Path) -> str:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def _needs_update(self, current_hash: str) -> bool:
        if not self.version_file.exists():
            return True
        # 简单校验：目录必须不为空
        if not any(self.target_dir.iterdir()):
            return True
        cached_hash = self.version_file.read_text().strip()
        return cached_hash != current_hash

    def _extract_assets(self, current_hash: str):
        print("[bold blue]📦 Upgrading runtime environment (Node.js + Frontend)...[/bold blue]")

        if self.target_dir.exists():
            try:
                shutil.rmtree(self.target_dir)
            except Exception as e:
                print(f"[yellow]⚠️  Could not clean old cache: {e}[/yellow]")

        self.target_dir.mkdir(parents=True, exist_ok=True)

        try:
            with tarfile.open(self.source_tar, "r:gz") as tar:
                # filter='data' 更加安全 (Python 3.12+)
                tar.extractall(path=self.target_dir, filter="data" if sys.version_info >= (3, 12) else None)

            self.version_file.write_text(current_hash)

            # 给二进制文件加权限
            node_path = Path(self._get_prod_paths()["node_bin"])
            if node_path.exists() and os.name != "nt":
                node_path.chmod(0o755)

            print("[bold green]✅ Assets extracted successfully.[/bold green]")
        except Exception as e:
            print(f"[bold red]❌ Failed to extract assets: {e}[/bold red]")
            # 失败时清理，避免残留损坏文件
            shutil.rmtree(self.target_dir, ignore_errors=True)
            sys.exit(1)

    def _get_prod_paths(self):
        node_name = "node.exe" if os.name == "nt" else "node"
        return {
            "node_bin": str(self.target_dir / node_name),
            "frontend_dir": self.target_dir / "frontend",
            "frontend_script": "server.js",
        }

    def _get_dev_paths(self):
        project_root = paths.bundle_dir  # 开发模式下 bundle_dir 指向项目根目录
        return {
            "node_bin": "node",
            "frontend_dir": project_root / "frontend",  # 假设你的源码在这里
            "frontend_script": "server.js",
        }


asset_manager = AssetManager()
