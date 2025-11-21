import asyncio
from typing import Protocol, Any
import json
import os
from enum import Enum
from pathlib import Path
from typing import Any

import httpx
import toml
from async_lru import alru_cache
from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, model_validator


from dingent.core.schemas import PluginRead

# Market repository configuration
MARKET_REPO_OWNER = "saya-ashen"
MARKET_REPO_NAME = "dingent-hub"
GITHUB_API_BASE = "https://api.github.com"
GITHUB_RAW_BASE = "https://ghfast.top//https://raw.githubusercontent.com"


MARKET_REPO_OWNER = "saya-ashen"
MARKET_REPO_NAME = "dingent-hub"
MARKET_BRANCH = "main"


class MarketItemCategory(str, Enum):
    """Enumeration for different categories of items in the Dingent Hub."""

    PLUGIN = "plugin"
    ASSISTANT = "assistant"
    WORKFLOW = "workflow"
    ALL = "all"

    def __str__(self) -> str:
        """Return the string value of the enum member."""
        return self.value


class MarketMetadata(BaseModel):
    version: str
    updated_at: str
    categories: dict[str, int]


class MarketItem(BaseModel):
    id: str
    name: str
    description: str | None = None
    version: str | None = None
    author: str | None = None
    category: MarketItemCategory
    tags: list[str] = []
    license: str | None = None
    readme: str | None = None
    downloads: int | None = None
    rating: float | None = None
    created_at: str | None = None
    updated_at: str | None = None
    is_installed: bool = False
    installed_version: str | None = None
    update_available: bool = False

    @model_validator(mode="before")
    @classmethod
    def _normalize_name_field(cls, data: Any) -> Any:
        if isinstance(data, dict):
            source_for_display_name = data.get("display_name") or data.get("name")
            if source_for_display_name:
                data["name"] = source_for_display_name

        return data


class MarketBackend(Protocol):
    @alru_cache(maxsize=1)
    async def get_metadata(self) -> MarketMetadata: ...
    async def list_items(
        self,
        category: MarketItemCategory,
        installed_fingerprint: tuple[tuple[str, tuple[tuple[str, str], ...]], ...],
    ) -> list[MarketItem]: ...
    async def get_readme(
        self,
        item_id: str,
        category: MarketItemCategory,
    ) -> str | None: ...
    async def download_item(
        self,
        item_id: str,
        category: MarketItemCategory,
        target_dir: Path,
    ) -> None: ...


class GitHubMarketBackend(MarketBackend):
    """Service for interacting with the dingent-market repository."""

    CATEGORY_TARGETS = {
        MarketItemCategory.PLUGIN: "plugins",
        MarketItemCategory.ASSISTANT: "config/assistants",
        MarketItemCategory.WORKFLOW: "config/workflows",
    }

    def __init__(self, log_manager):
        self._log_manager = log_manager

        auth_token = os.getenv("GITHUB_TOKEN")
        headers = {"User-Agent": "Dingent-Market-Client/1.0"}
        if auth_token:
            headers["Authorization"] = f"token {auth_token}"

        self.client = httpx.AsyncClient(
            headers=headers,
            timeout=30.0,
            follow_redirects=True,
        )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _category_repo_dir(category: MarketItemCategory) -> str:
        """Return the repo directory name for a given category."""
        return f"{category.value}s"

    @staticmethod
    def _build_installed_fingerprint(
        installed_items: dict[str, list[PluginRead | Any]],
    ) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
        """
        Build a stable, hashable fingerprint of installed items.

        Structure:
        (
          ("plugins", (("plugin_a", "1.0.0"), ("plugin_b", "2.0.0"))),
          ("workflows", (("wf_x", "0.1.0"),)),
        )
        """
        if not installed_items:
            return ()

        result: list[tuple[str, tuple[tuple[str, str], ...]]] = []

        for category_name, items in sorted(installed_items.items()):
            pairs: list[tuple[str, str]] = []

            for obj in items:
                # Prefer PluginRead
                if isinstance(obj, PluginRead):
                    item_id = obj.registry_id
                    version = getattr(obj, "version", "") or ""
                # Then try dict-like (e.g., JSON from API)
                elif isinstance(obj, dict):
                    item_id = obj.get("registry_id") or obj.get("id") or obj.get("name") or ""
                    version = obj.get("version", "") or ""
                else:
                    # Fallback: use attributes if exist, otherwise str(obj)
                    item_id = getattr(obj, "registry_id", None) or getattr(obj, "id", None) or str(obj)
                    version = getattr(obj, "version", "") or ""

                if not item_id:
                    continue
                pairs.append((str(item_id), str(version)))

            # Ensure deterministic order
            pairs.sort(key=lambda t: t[0])
            result.append((category_name, tuple(pairs)))

        # Also sort categories by name for deterministic fingerprint
        result.sort(key=lambda t: t[0])
        return tuple(result)

    async def close(self):
        """Close the HTTP session."""
        await self.client.aclose()

    async def _fetch_url_as_text(self, url: str) -> str | None:
        """A reusable helper to fetch content from a URL as text."""
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.RequestError as e:
            self._log_manager.log_with_context(
                "warning",
                "Failed to fetch URL",
                context={"url": str(getattr(e.request, "url", url)), "error": str(e)},
            )
            return None

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    @alru_cache(maxsize=1)
    async def get_metadata(self) -> MarketMetadata:
        """Fetch market metadata from the market.json file."""
        url = f"{GITHUB_RAW_BASE}/{MARKET_REPO_OWNER}/{MARKET_REPO_NAME}/main/market.json"
        content = await self._fetch_url_as_text(url)
        if content:
            try:
                return MarketMetadata.model_validate_json(content)
            except Exception as e:
                self._log_manager.log_with_context(
                    "warning",
                    "Failed to parse market metadata",
                    context={"error": str(e)},
                )

        # Fallback metadata on failure
        return MarketMetadata(version="0.0.0", updated_at="", categories={})

    async def list_items(
        self,
        category: MarketItemCategory,
        installed_fingerprint: tuple[tuple[str, tuple[tuple[str, str], ...]], ...],
    ) -> list[MarketItem]:
        """
        Fetch a list of available market items concurrently.

        installed_items 结构示例：
        {
          "plugins": [PluginRead(...), ...],
          "workflows": [...],
        }
        """
        # installed_items = installed_fingerprint or {}
        # installed_fingerprint = self._build_installed_fingerprint(installed_items)

        categories_to_fetch = [c for c in MarketItemCategory if c != MarketItemCategory.ALL] if category == MarketItemCategory.ALL else [category]

        tasks = [self._fetch_category_items(cat, installed_fingerprint) for cat in categories_to_fetch]
        results = await asyncio.gather(*tasks)

        all_items: list[MarketItem] = [item for sublist in results for item in sublist]
        return all_items

    async def get_readme(self, item_id: str, category: MarketItemCategory) -> str | None:
        """Get README content for a specific item."""
        try:
            readme_path = f"{self._category_repo_dir(category)}/{item_id}/README.md"
            url = f"{GITHUB_RAW_BASE}/{MARKET_REPO_OWNER}/{MARKET_REPO_NAME}/main/{readme_path}"

            response = await self.client.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self._log_manager.log_with_context(
                "warning",
                "Failed to fetch README",
                context={"item_id": item_id, "category": category.value, "error": str(e)},
            )
            return None

    # -------------------------------------------------------------------------
    # Category / item fetching
    # -------------------------------------------------------------------------

    @alru_cache(maxsize=16)
    async def _fetch_category_items(
        self,
        category_enum: MarketItemCategory,
        installed_items_tuple: tuple[tuple[str, tuple[tuple[str, str], ...]], ...],
    ) -> list[MarketItem]:
        """Fetch and process all items for a specific category concurrently."""
        try:
            repo_directory = self._category_repo_dir(category_enum)
            url = f"{GITHUB_API_BASE}/repos/{MARKET_REPO_OWNER}/{MARKET_REPO_NAME}/contents/{repo_directory}"

            content = await self._fetch_url_as_text(url)
            if not content:
                return []

            entries = json.loads(content)
            directories = [dir_info["name"] for dir_info in entries if dir_info.get("type") == "dir"]

            category_key = repo_directory  # e.g. "plugins", "assistants"
            relevant_versions_tuple: tuple[tuple[str, str], ...] = next(
                (versions for cat, versions in installed_items_tuple if cat == category_key),
                (),
            )

            tasks = [self._fetch_item_details(category_enum, item_id, relevant_versions_tuple) for item_id in directories]
            results = await asyncio.gather(*tasks)
            return [item for item in results if item is not None]
        except Exception as e:
            self._log_manager.log_with_context(
                "warning",
                "Failed to fetch category items",
                context={"category": category_enum.value, "error": str(e)},
            )
            return []

    async def _get_plugin_meta(self, item_id: str) -> dict:
        """Fetches and merges pyproject.toml and plugin.toml for a plugin."""
        final_meta: dict[str, Any] = {}
        repo_dir = self._category_repo_dir(MarketItemCategory.PLUGIN)

        # 1. Optional pyproject.toml
        pyproject_url = f"{GITHUB_RAW_BASE}/{MARKET_REPO_OWNER}/{MARKET_REPO_NAME}/main/{repo_dir}/{item_id}/pyproject.toml"
        pyproject_content = await self._fetch_url_as_text(pyproject_url)
        if pyproject_content:
            pyproject_data = toml.loads(pyproject_content)
            final_meta.update(pyproject_data.get("project", {}))

        # 2. Required plugin.toml
        plugin_url = f"{GITHUB_RAW_BASE}/{MARKET_REPO_OWNER}/{MARKET_REPO_NAME}/main/{repo_dir}/{item_id}/plugin.toml"
        plugin_content = await self._fetch_url_as_text(plugin_url)
        if not plugin_content:
            raise FileNotFoundError("plugin.toml is required but was not found.")

        plugin_data = toml.loads(plugin_content)
        plugin_meta = plugin_data.get("plugin", plugin_data)
        final_meta.update(plugin_meta)
        return final_meta

    @alru_cache(maxsize=128)
    async def _fetch_item_details(
        self,
        category_enum: MarketItemCategory,
        item_id: str,
        installed_versions_tuple: tuple[tuple[str, str], ...],
    ) -> MarketItem | None:
        """Fetch details for a specific item, merging configs if necessary."""
        installed_items = dict(installed_versions_tuple)

        try:
            if category_enum == MarketItemCategory.PLUGIN:
                final_meta = await self._get_plugin_meta(item_id)
            else:
                self._log_manager.log_with_context(
                    "warning",
                    "Config fetching for '{cat}' is not yet implemented.",
                    context={"cat": category_enum.value},
                )
                return None

            is_item_installed = item_id in installed_items
            installed_version = installed_items.get(item_id)
            remote_version = str(final_meta.get("version", "0.0.0"))
            update_available = False

            if is_item_installed and installed_version:
                try:
                    if Version(remote_version) > Version(installed_version):
                        update_available = True
                except InvalidVersion:
                    pass

            return MarketItem(
                id=item_id,
                name=final_meta.get("name", item_id),
                description=final_meta.get("description"),
                version=str(final_meta.get("version", "1.0.0")),
                author=final_meta.get("author"),
                category=category_enum,
                tags=list(final_meta.get("tags", [])),
                license=(final_meta.get("license", {}) or {}).get("text") or "License not specified",
                is_installed=is_item_installed,
                installed_version=installed_version,
                update_available=update_available,
            )
        except Exception as e:
            self._log_manager.log_with_context(
                "warning",
                "Failed to fetch item details, using fallback",
                context={"item_id": item_id, "category": category_enum.value, "error": str(e)},
            )
            # Fallback if any step fails
            return MarketItem(
                id=item_id,
                name=item_id.replace("-", " ").title(),
                description=f"A {category_enum.value} from the market",
                category=category_enum,
                version="1.0.0",
                is_installed=(item_id in installed_items),
                installed_version=installed_items.get(item_id),
                update_available=False,
            )

    # -------------------------------------------------------------------------
    # Download / install
    # -------------------------------------------------------------------------

    async def download_item(self, item_id, category, target_dir):
        await self._install_item(item_id, category, target_dir)

    async def _download_directory(self, source_path: str, target_dir: Path):
        """Download all files from a directory in the repository."""
        try:
            url = f"{GITHUB_API_BASE}/repos/{MARKET_REPO_OWNER}/{MARKET_REPO_NAME}/contents/{source_path}"
            content_json = await self._fetch_url_as_text(url)
            if not content_json:
                return

            contents = json.loads(content_json)
            download_tasks = []

            for item in contents:
                item_type = item.get("type")
                if item_type == "file":
                    file_path = target_dir / item["name"]
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    task = self._download_file(item["download_url"], file_path)
                    download_tasks.append(task)
                elif item_type == "dir":
                    subdir_path = target_dir / item["name"]
                    subdir_path.mkdir(parents=True, exist_ok=True)
                    task = self._download_directory(f"{source_path}/{item['name']}", subdir_path)
                    download_tasks.append(task)

            if download_tasks:
                await asyncio.gather(*download_tasks)
        except Exception as e:
            self._log_manager.log_with_context(
                "error",
                "Failed to download directory",
                context={"source_path": source_path, "error": str(e)},
            )
            raise

    async def _download_file(self, url: str, path: Path):
        """Download a single file to the given path."""
        try:
            async with self.client.stream("GET", url) as response:
                response.raise_for_status()
                with open(path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
            self._log_manager.log_with_context("info", "Downloaded file", context={"file": str(path)})
        except httpx.RequestError as e:
            self._log_manager.log_with_context(
                "error",
                "Failed to download file",
                context={"url": url, "error": str(e)},
            )

    async def _install_item(self, item_id: str, category: MarketItemCategory, target_dir: Path):
        """Perform category-specific installation steps."""
        try:
            if category == MarketItemCategory.PLUGIN:
                await self._install_plugin(item_id, target_dir)
            elif category == MarketItemCategory.ASSISTANT:
                await self._install_assistant(item_id, target_dir)
            elif category == MarketItemCategory.WORKFLOW:
                await self._install_workflow(item_id, target_dir)
        except Exception as e:
            self._log_manager.log_with_context(
                "error",
                "Installation failed",
                context={"item_id": item_id, "category": category.value, "error": str(e)},
            )
            raise

    async def _install_plugin(self, plugin_id: str, target_dir: Path):
        """Install a plugin."""
        # TODO: Register plugin with plugin manager
        self._log_manager.log_with_context(
            "info",
            "Plugin installed",
            context={"plugin_id": plugin_id, "path": str(target_dir)},
        )

    async def _install_assistant(self, assistant_id: str, target_dir: Path):
        """Install an assistant configuration."""
        # TODO: Register assistant with config manager
        self._log_manager.log_with_context(
            "info",
            "Assistant installed",
            context={"assistant_id": assistant_id, "path": str(target_dir)},
        )

    async def _install_workflow(self, workflow_id: str, target_dir: Path):
        """Install a workflow configuration."""
        # TODO: Register workflow with workflow manager
        self._log_manager.log_with_context(
            "info",
            "Workflow installed",
            context={"workflow_id": workflow_id, "path": str(target_dir)},
        )


class MarketService:
    CATEGORY_TARGETS = {
        MarketItemCategory.PLUGIN: "plugins",
        MarketItemCategory.ASSISTANT: "config/assistants",
        MarketItemCategory.WORKFLOW: "config/workflows",
    }

    def __init__(self, project_root: Path, log_manager, backend: MarketBackend):
        self.project_root = project_root
        self._log_manager = log_manager
        self._backend = backend

    async def get_market_metadata(self) -> MarketMetadata:
        return await self._backend.get_metadata()

    @staticmethod
    def _build_installed_fingerprint(
        installed_items: dict[str, list[PluginRead | Any]],
    ) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
        """
        Build a stable, hashable fingerprint of installed items.

        Structure:
        (
          ("plugins", (("plugin_a", "1.0.0"), ("plugin_b", "2.0.0"))),
          ("workflows", (("wf_x", "0.1.0"),)),
        )
        """
        if not installed_items:
            return ()

        result: list[tuple[str, tuple[tuple[str, str], ...]]] = []

        for category_name, items in sorted(installed_items.items()):
            pairs: list[tuple[str, str]] = []

            for obj in items:
                # Prefer PluginRead
                if isinstance(obj, PluginRead):
                    item_id = obj.registry_id
                    version = getattr(obj, "version", "") or ""
                # Then try dict-like (e.g., JSON from API)
                elif isinstance(obj, dict):
                    item_id = obj.get("registry_id") or obj.get("id") or obj.get("name") or ""
                    version = obj.get("version", "") or ""
                else:
                    # Fallback: use attributes if exist, otherwise str(obj)
                    item_id = getattr(obj, "registry_id", None) or getattr(obj, "id", None) or str(obj)
                    version = getattr(obj, "version", "") or ""

                if not item_id:
                    continue
                pairs.append((str(item_id), str(version)))

            # Ensure deterministic order
            pairs.sort(key=lambda t: t[0])
            result.append((category_name, tuple(pairs)))

        # Also sort categories by name for deterministic fingerprint
        result.sort(key=lambda t: t[0])
        return tuple(result)

    async def get_market_items(
        self,
        category: MarketItemCategory,
        installed_items: dict[str, list[PluginRead | Any]] | None = None,
    ) -> list[MarketItem]:
        installed_items = installed_items or {}
        installed_fingerprint = self._build_installed_fingerprint(installed_items)
        return await self._backend.list_items(category, installed_fingerprint)

    async def get_item_readme(self, item_id: str, category: MarketItemCategory) -> str | None:
        return await self._backend.get_readme(item_id, category)

    async def _install_plugin(self, plugin_id: str, target_dir: Path):
        """Install a plugin."""
        # TODO: Register plugin with plugin manager
        self._log_manager.log_with_context(
            "info",
            "Plugin installed",
            context={"plugin_id": plugin_id, "path": str(target_dir)},
        )

    async def _install_assistant(self, assistant_id: str, target_dir: Path):
        """Install an assistant configuration."""
        # TODO: Register assistant with config manager
        self._log_manager.log_with_context(
            "info",
            "Assistant installed",
            context={"assistant_id": assistant_id, "path": str(target_dir)},
        )

    async def _install_workflow(self, workflow_id: str, target_dir: Path):
        """Install a workflow configuration."""
        # TODO: Register workflow with workflow manager
        self._log_manager.log_with_context(
            "info",
            "Workflow installed",
            context={"workflow_id": workflow_id, "path": str(target_dir)},
        )

    async def _install_item(self, item_id: str, category: MarketItemCategory, target_dir: Path):
        """Perform category-specific installation steps."""
        try:
            if category == MarketItemCategory.PLUGIN:
                await self._install_plugin(item_id, target_dir)
            elif category == MarketItemCategory.ASSISTANT:
                await self._install_assistant(item_id, target_dir)
            elif category == MarketItemCategory.WORKFLOW:
                await self._install_workflow(item_id, target_dir)
        except Exception as e:
            self._log_manager.log_with_context(
                "error",
                "Installation failed",
                context={"item_id": item_id, "category": category.value, "error": str(e)},
            )
            raise

    async def download_item(self, item_id: str, category: MarketItemCategory) -> dict[str, Any]:
        try:
            target_path_suffix = self.CATEGORY_TARGETS.get(category)
            if not target_path_suffix:
                raise ValueError(f"Cannot download category: {category}")

            target_dir = self.project_root / target_path_suffix
            if category == MarketItemCategory.PLUGIN:
                target_dir = target_dir / item_id
            target_dir.mkdir(parents=True, exist_ok=True)

            await self._backend.download_item(item_id, category, target_dir)

            await self._install_item(item_id, category, target_dir)
            return {
                "success": True,
                "message": f"Successfully downloaded {category.value}: {item_id}",
                "installed_path": str(target_dir.relative_to(self.project_root)),
            }
        except Exception as e:
            self._log_manager.log_with_context(
                "error",
                "Download failed",
                context={"item_id": item_id, "category": category.value, "error": str(e)},
            )
            return {
                "success": False,
                "message": f"Failed to download {category.value} '{item_id}': {str(e)}",
                "installed_path": None,
            }
