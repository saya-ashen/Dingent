import asyncio
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

from dingent.core.log_manager import LogManager

# Market repository configuration
MARKET_REPO_OWNER = "saya-ashen"
MARKET_REPO_NAME = "dingent-hub"
GITHUB_API_BASE = "https://api.github.com"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"


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


class MarketService:
    """Service for interacting with the dingent-market repository."""

    CATEGORY_TARGETS = {
        MarketItemCategory.PLUGIN: "plugins",
        MarketItemCategory.ASSISTANT: "config/assistants",
        MarketItemCategory.WORKFLOW: "config/workflows",
    }

    def __init__(self, project_root: Path, log_manager: LogManager):
        self.project_root = project_root
        self._log_manager = log_manager
        auth_token = os.getenv("GITHUB_TOKEN")  # From environment variables
        headers = {"User-Agent": "Dingent-Market-Client/1.0"}
        if auth_token:
            headers["Authorization"] = f"token {auth_token}"
        self.client = httpx.AsyncClient(
            headers=headers,
            timeout=30.0,
            follow_redirects=True,
        )

    async def close(self):
        """Close the HTTP session."""
        await self.client.aclose()

    async def _fetch_url_as_text(self, url: str) -> str | None:
        """A reusable helper to fetch content from a URL."""
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.RequestError as e:
            self._log_manager.log_with_context("warning", "Failed to fetch URL: {url}", context={"url": str(e.request.url), "error": str(e)})
            return None

    @alru_cache(maxsize=1)
    async def get_market_metadata(self) -> MarketMetadata:
        """Fetch market metadata from the market.json file."""
        url = f"{GITHUB_RAW_BASE}/{MARKET_REPO_OWNER}/{MARKET_REPO_NAME}/main/market.json"
        content = await self._fetch_url_as_text(url)
        if content:
            try:
                return MarketMetadata.model_validate_json(content)
            except Exception as e:
                self._log_manager.log_with_context("warning", "Failed to parse market metadata", context={"error": str(e)})

        # Return fallback metadata on failure
        return MarketMetadata(version="0.0.0", updated_at="", categories={})

    async def get_market_items(
        self,
        category: MarketItemCategory,
        installed_items: dict[str, dict[str, str]] | None = None,
    ) -> list[MarketItem]:
        """Fetch a list of available market items concurrently."""
        if installed_items is None:
            installed_items = {}
        hashable_installed_items = tuple((category_name, tuple(sorted(versions.items()))) for category_name, versions in sorted(installed_items.items()))
        categories_to_fetch = [c for c in MarketItemCategory if c != MarketItemCategory.ALL] if category == MarketItemCategory.ALL else [category]

        tasks = [self._fetch_category_items(f"{cat.value}s", cat, hashable_installed_items) for cat in categories_to_fetch]
        results = await asyncio.gather(*tasks)

        all_items = [item for sublist in results for item in sublist]
        return all_items

    @alru_cache(maxsize=16)  # Cache listings for a few categories
    async def _fetch_category_items(
        self,
        repo_directory: str,
        category_enum: MarketItemCategory,
        installed_items_tuple: tuple,
    ) -> list[MarketItem]:
        """Fetch and process all items for a specific category concurrently."""
        try:
            url = f"{GITHUB_API_BASE}/repos/{MARKET_REPO_OWNER}/{MARKET_REPO_NAME}/contents/{repo_directory}"
            content = await self._fetch_url_as_text(url)
            if not content:
                return []

            directories = [dir_info["name"] for dir_info in json.loads(content) if dir_info.get("type") == "dir"]
            category_key = f"{category_enum.value}s"
            relevant_versions_tuple = next(
                (versions for cat, versions in installed_items_tuple if cat == category_key),
                (),
            )

            tasks = [self._fetch_item_details(repo_directory, category_enum, item_id, relevant_versions_tuple) for item_id in directories]
            results = await asyncio.gather(*tasks)
            return [item for item in results if item]

        except Exception as e:
            self._log_manager.log_with_context("warning", "Failed to fetch category items", context={"category": category_enum.value, "error": str(e)})
            return []

    async def _get_plugin_meta(self, repo_dir: str, item_id: str) -> dict:
        """Fetches and merges pyproject.toml and plugin.toml for a plugin."""
        final_meta = {}
        # 1. Fetch optional pyproject.toml
        pyproject_url = f"{GITHUB_RAW_BASE}/{MARKET_REPO_OWNER}/{MARKET_REPO_NAME}/main/{repo_dir}/{item_id}/pyproject.toml"
        pyproject_content = await self._fetch_url_as_text(pyproject_url)
        if pyproject_content:
            pyproject_data = toml.loads(pyproject_content)
            final_meta.update(pyproject_data.get("project", {}))

        # 2. Fetch required plugin.toml (and overwrite any conflicts)
        plugin_url = f"{GITHUB_RAW_BASE}/{MARKET_REPO_OWNER}/{MARKET_REPO_NAME}/main/{repo_dir}/{item_id}/plugin.toml"
        plugin_content = await self._fetch_url_as_text(plugin_url)
        if not plugin_content:
            raise FileNotFoundError("plugin.toml is required but was not found.")

        plugin_data = toml.loads(plugin_content)
        plugin_meta = plugin_data.get("plugin", plugin_data)
        final_meta.update(plugin_meta)
        return final_meta

    @alru_cache(maxsize=128)  # Cache details for many individual items
    async def _fetch_item_details(
        self,
        repo_directory: str,
        category_enum: MarketItemCategory,
        item_id: str,
        installed_versions_tuple: tuple[tuple[str, str], ...],
    ) -> MarketItem | None:
        """Fetch details for a specific item, merging configs if necessary."""
        installed_items = dict(installed_versions_tuple)
        try:
            final_meta = {}
            # The merging logic is specific to plugins
            if category_enum == MarketItemCategory.PLUGIN:
                final_meta = await self._get_plugin_meta(repo_directory, item_id)
            else:
                self._log_manager.log_with_context("warning", "Config fetching for '{cat}' is not yet implemented.", context={"cat": category_enum.value})
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
                tags=final_meta.get("tags", []),
                license=final_meta.get("license", {}).get("text") or "License not specified",
                is_installed=is_item_installed,
                installed_version=installed_version,
                update_available=update_available,
            )
        except Exception as e:
            self._log_manager.log_with_context(
                "warning", "Failed to fetch item details, using fallback", context={"item_id": item_id, "category": category_enum.value, "error": str(e)}
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

    async def download_item(self, item_id: str, category: MarketItemCategory) -> dict[str, Any]:
        """Download and install a market item."""
        try:
            target_path_suffix = self.CATEGORY_TARGETS.get(category)
            if not target_path_suffix:
                raise ValueError(f"Cannot download category: {category}")
            target_dir = self.project_root / target_path_suffix

            if category == MarketItemCategory.PLUGIN:
                target_dir = target_dir / item_id

            target_dir.mkdir(parents=True, exist_ok=True)

            source_path = f"{category.value}s/{item_id}"
            await self._download_directory(source_path, target_dir)

            await self._install_item(item_id, category, target_dir)

            return {"success": True, "message": f"Successfully downloaded {category.value}: {item_id}", "installed_path": str(target_dir.relative_to(self.project_root))}
        except Exception as e:
            self._log_manager.log_with_context("error", "Download failed", context={"item_id": item_id, "category": category.value, "error": str(e)})
            return {"success": False, "message": f"Failed to download {category.value} '{item_id}': {str(e)}", "installed_path": None}

    async def _download_directory(self, source_path: str, target_dir: Path):
        """Download all files from a directory in the repository."""
        try:
            # Get directory listing
            url = f"{GITHUB_API_BASE}/repos/{MARKET_REPO_OWNER}/{MARKET_REPO_NAME}/contents/{source_path}"
            content_json = await self._fetch_url_as_text(url)
            if not content_json:
                return

            contents = json.loads(content_json)
            download_tasks = []

            for item in contents:
                if item["type"] == "file":
                    task = self._download_file(item["download_url"], target_dir / item["name"])
                    download_tasks.append(task)
                elif item["type"] == "dir":
                    subdir_path = target_dir / item["name"]
                    subdir_path.mkdir(exist_ok=True)
                    task = self._download_directory(f"{source_path}/{item['name']}", subdir_path)
                    download_tasks.append(task)
            if download_tasks:
                await asyncio.gather(*download_tasks)
        except Exception as e:
            self._log_manager.log_with_context("error", "Failed to download directory", context={"source_path": source_path, "error": str(e)})
            raise

    async def _download_file(self, url: str, path: Path):
        """Downloads a single file to the given path."""
        try:
            async with self.client.stream("GET", url) as response:
                response.raise_for_status()
                with open(path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
            self._log_manager.log_with_context("info", "Downloaded file: {file}", context={"file": str(path)})
        except httpx.RequestError as e:
            self._log_manager.log_with_context("error", "Failed to download file", context={"url": url, "error": str(e)})

    async def _install_item(self, item_id: str, category: MarketItemCategory, target_dir: Path):
        """Perform category-specific installation steps."""
        try:
            # Using enum members for comparison
            if category == MarketItemCategory.PLUGIN:
                await self._install_plugin(item_id, target_dir)
            elif category == MarketItemCategory.ASSISTANT:
                await self._install_assistant(item_id, target_dir)
            elif category == MarketItemCategory.WORKFLOW:
                await self._install_workflow(item_id, target_dir)
        except Exception as e:
            self._log_manager.log_with_context("error", "Installation failed", context={"item_id": item_id, "category": category.value, "error": str(e)})
            raise

    async def _install_plugin(self, plugin_id: str, target_dir: Path):
        """Install a plugin."""
        # TODO: Register plugin with plugin manager
        # For now, just ensure it's in the right place
        self._log_manager.log_with_context("info", "Plugin installed", context={"plugin_id": plugin_id, "path": str(target_dir)})

    async def _install_assistant(self, assistant_id: str, target_dir: Path):
        """Install an assistant configuration."""
        # TODO: Register assistant with config manager
        self._log_manager.log_with_context("info", "Assistant installed", context={"assistant_id": assistant_id, "path": str(target_dir)})

    async def _install_workflow(self, workflow_id: str, target_dir: Path):
        """Install a workflow configuration."""
        # TODO: Register workflow with workflow manager
        self._log_manager.log_with_context("info", "Workflow installed", context={"workflow_id": workflow_id, "path": str(target_dir)})

    async def get_item_readme(self, item_id: str, category: MarketItemCategory) -> str | None:
        """Get README content for a specific item."""
        try:
            # The repo directory is the plural of the enum value
            readme_path = f"{category.value}s/{item_id}/README.md"
            url = f"{GITHUB_RAW_BASE}/{MARKET_REPO_OWNER}/{MARKET_REPO_NAME}/main/{readme_path}"

            response = await self.client.get(url)
            response.raise_for_status()

            return response.text
        except Exception as e:
            self._log_manager.log_with_context("warning", "Failed to fetch README", context={"item_id": item_id, "category": category.value, "error": str(e)})
            return None
