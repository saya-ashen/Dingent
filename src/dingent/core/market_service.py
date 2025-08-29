"""
Market service for downloading and installing plugins, assistants, and workflows
from the dingent-market repository.
"""

import asyncio
import json
import logging
import zipfile
from pathlib import Path
from typing import Any

import requests
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Market repository configuration
MARKET_REPO_OWNER = "saya-ashen"
MARKET_REPO_NAME = "dingent-market"
GITHUB_API_BASE = "https://api.github.com"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"


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
    category: str  # "plugin" | "assistant" | "workflow"
    tags: list[str] = []
    license: str | None = None
    readme: str | None = None
    downloads: int | None = None
    rating: float | None = None
    created_at: str | None = None
    updated_at: str | None = None


class MarketService:
    """Service for interacting with the dingent-market repository."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Dingent-Market-Client/1.0"
        })

    def close(self):
        """Close the HTTP session."""
        self.session.close()

    async def get_market_metadata(self) -> MarketMetadata:
        """Fetch market metadata from the market.json file."""
        try:
            url = f"{GITHUB_RAW_BASE}/{MARKET_REPO_OWNER}/{MARKET_REPO_NAME}/main/market.json"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return MarketMetadata(**data)
        except Exception as e:
            logger.warning(f"Failed to fetch market metadata: {e}")
            # Return fallback metadata
            return MarketMetadata(
                version="1.0.0",
                updated_at="2024-08-29T00:00:00Z",
                categories={"plugins": 0, "assistants": 0, "workflows": 0}
            )

    async def get_market_items(self, category: str | None = None) -> list[MarketItem]:
        """Fetch list of available market items."""
        try:
            # First, get the market metadata
            metadata = await self.get_market_metadata()
            
            # Then fetch directory listings for each category
            items = []
            categories_to_fetch = [category] if category else ["plugins", "assistants", "workflows"]
            
            for cat in categories_to_fetch:
                cat_items = await self._fetch_category_items(cat)
                items.extend(cat_items)
            
            return items
        except Exception as e:
            logger.warning(f"Failed to fetch market items: {e}")
            return []

    async def _fetch_category_items(self, category: str) -> list[MarketItem]:
        """Fetch items for a specific category."""
        try:
            # Get directory listing from GitHub API
            url = f"{GITHUB_API_BASE}/repos/{MARKET_REPO_OWNER}/{MARKET_REPO_NAME}/contents/{category}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            directories = response.json()
            items = []
            
            for dir_info in directories:
                if dir_info.get("type") == "dir":
                    item_id = dir_info["name"]
                    item = await self._fetch_item_details(category, item_id)
                    if item:
                        items.append(item)
            
            return items
        except Exception as e:
            logger.warning(f"Failed to fetch {category} items: {e}")
            return []

    async def _fetch_item_details(self, category: str, item_id: str) -> MarketItem | None:
        """Fetch details for a specific item."""
        try:
            # Try to get item metadata from a manifest file
            manifest_path = f"{category}/{item_id}/manifest.json"
            url = f"{GITHUB_RAW_BASE}/{MARKET_REPO_OWNER}/{MARKET_REPO_NAME}/main/{manifest_path}"
            
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                manifest = response.json()
                
                return MarketItem(
                    id=item_id,
                    name=manifest.get("name", item_id),
                    description=manifest.get("description"),
                    version=manifest.get("version"),
                    author=manifest.get("author"),
                    category=category.rstrip("s"),  # Remove 's' from category name
                    tags=manifest.get("tags", []),
                    license=manifest.get("license"),
                    downloads=manifest.get("downloads"),
                    rating=manifest.get("rating"),
                    created_at=manifest.get("created_at"),
                    updated_at=manifest.get("updated_at")
                )
            except Exception:
                # If no manifest, create basic item from directory name
                return MarketItem(
                    id=item_id,
                    name=item_id.replace("-", " ").title(),
                    description=f"A {category.rstrip('s')} from the market",
                    category=category.rstrip("s"),
                    version="1.0.0"
                )
        except Exception as e:
            logger.warning(f"Failed to fetch details for {category}/{item_id}: {e}")
            return None

    async def download_item(self, item_id: str, category: str) -> dict[str, Any]:
        """Download and install a market item."""
        try:
            # Determine target directory based on category
            if category == "plugin":
                target_dir = self.project_root / "plugins" / item_id
            elif category == "assistant":
                target_dir = self.project_root / "config" / "assistants" / item_id
            elif category == "workflow":
                target_dir = self.project_root / "config" / "workflows" / item_id
            else:
                raise ValueError(f"Unknown category: {category}")

            # Create target directory
            target_dir.mkdir(parents=True, exist_ok=True)

            # Download files for the item
            source_path = f"{category}s/{item_id}"  # Add 's' for directory name
            await self._download_directory(source_path, target_dir)

            # Perform category-specific installation steps
            await self._install_item(item_id, category, target_dir)

            return {
                "success": True,
                "message": f"Successfully downloaded {category}: {item_id}",
                "installed_path": str(target_dir.relative_to(self.project_root))
            }
        except Exception as e:
            logger.error(f"Failed to download {category} '{item_id}': {e}")
            return {
                "success": False,
                "message": f"Failed to download {category} '{item_id}': {str(e)}",
                "installed_path": None
            }

    async def _download_directory(self, source_path: str, target_dir: Path):
        """Download all files from a directory in the repository."""
        try:
            # Get directory listing
            url = f"{GITHUB_API_BASE}/repos/{MARKET_REPO_OWNER}/{MARKET_REPO_NAME}/contents/{source_path}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            contents = response.json()
            
            # Download each file
            for item in contents:
                if item["type"] == "file":
                    file_url = item["download_url"]
                    file_path = target_dir / item["name"]
                    
                    file_response = self.session.get(file_url, timeout=30)
                    file_response.raise_for_status()
                    
                    # Write file content
                    with open(file_path, "wb") as f:
                        f.write(file_response.content)
                    
                    logger.info(f"Downloaded {item['name']} to {file_path}")
                elif item["type"] == "dir":
                    # Recursively download subdirectories
                    subdir_path = target_dir / item["name"]
                    subdir_path.mkdir(exist_ok=True)
                    await self._download_directory(f"{source_path}/{item['name']}", subdir_path)
                    
        except Exception as e:
            logger.error(f"Failed to download directory {source_path}: {e}")
            raise

    async def _install_item(self, item_id: str, category: str, target_dir: Path):
        """Perform category-specific installation steps."""
        try:
            if category == "plugin":
                await self._install_plugin(item_id, target_dir)
            elif category == "assistant":
                await self._install_assistant(item_id, target_dir)
            elif category == "workflow":
                await self._install_workflow(item_id, target_dir)
        except Exception as e:
            logger.error(f"Failed to install {category} {item_id}: {e}")
            raise

    async def _install_plugin(self, plugin_id: str, target_dir: Path):
        """Install a plugin."""
        # TODO: Register plugin with plugin manager
        # For now, just ensure it's in the right place
        logger.info(f"Plugin {plugin_id} installed to {target_dir}")

    async def _install_assistant(self, assistant_id: str, target_dir: Path):
        """Install an assistant configuration."""
        # TODO: Register assistant with config manager
        logger.info(f"Assistant {assistant_id} installed to {target_dir}")

    async def _install_workflow(self, workflow_id: str, target_dir: Path):
        """Install a workflow configuration."""
        # TODO: Register workflow with workflow manager
        logger.info(f"Workflow {workflow_id} installed to {target_dir}")

    async def get_item_readme(self, item_id: str, category: str) -> str | None:
        """Get README content for a specific item."""
        try:
            readme_path = f"{category}s/{item_id}/README.md"
            url = f"{GITHUB_RAW_BASE}/{MARKET_REPO_OWNER}/{MARKET_REPO_NAME}/main/{readme_path}"
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            return response.text
        except Exception as e:
            logger.warning(f"Failed to fetch README for {category}/{item_id}: {e}")
            return None