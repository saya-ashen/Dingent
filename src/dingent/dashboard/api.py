import os
from typing import Any

import requests
import streamlit as st

from dingent.core.types import AssistantCreate

# --- Configuration ---
BACKEND_URL = os.getenv("DING_BACKEND_ADMIN_URL", "http://127.0.0.1:2024")
HTTP_TIMEOUT = 120  # seconds
SESSION = requests.Session()


@st.cache_data(ttl=5, show_spinner="Loading app settings...")
def get_app_settings() -> dict[str, Any] | None:
    """Fetch core application configuration from the backend."""
    try:
        resp = SESSION.get(f"{BACKEND_URL}/config/settings", timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch app settings: {e}")
        return None
    except Exception as e:
        st.error(f"An error occurred while processing app settings: {e}")
        return None


@st.cache_data(ttl=5, show_spinner="Loading assistants configuration...")
def get_assistants_config() -> list[dict[str, Any]] | None:
    """Fetch the list of assistant configurations from the backend."""
    try:
        resp = SESSION.get(f"{BACKEND_URL}/assistants", timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch assistants configuration: {e}")
        return None
    except Exception as e:
        st.error(f"An error occurred while processing assistants configuration: {e}")
        return None


@st.cache_data(ttl=30, show_spinner="Loading available plugins...")
def get_available_plugins() -> list[dict[str, Any]] | None:
    """Fetch the manifest of all available plugins from the backend."""
    try:
        resp = SESSION.get(f"{BACKEND_URL}/plugins/list", timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch available plugins: {e}")
        return None
    except Exception as e:
        st.error(f"An unknown error occurred while processing plugins list: {e}")
        return None


def add_assistant(assistant_data: AssistantCreate) -> bool:
    try:
        resp = SESSION.post(
            f"{BACKEND_URL}/assistants/add_assistant",
            json=assistant_data.model_dump(mode="json"),
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        get_app_settings.clear()
        return True
    except requests.exceptions.RequestException as e:
        # Try extracting a more readable error message from the response body
        detail = getattr(e, "response", None)
        try:
            msg = detail.json().get("detail", str(e)) if detail else str(e)
        except Exception:
            msg = detail.text if detail and hasattr(detail, "text") else str(e)
        st.error(f"Failed to add assistant: {msg}")
        return False


def save_app_settings(settings_data: dict[str, Any]) -> bool:
    """Send core application configuration to the backend."""
    try:
        resp = SESSION.post(f"{BACKEND_URL}/config/settings", json=settings_data, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        get_app_settings.clear()
        return True
    except requests.exceptions.RequestException as e:
        # Try extracting a more readable error message from the response body
        detail = getattr(e, "response", None)
        try:
            msg = detail.json().get("detail", str(e)) if detail else str(e)
        except Exception:
            msg = detail.text if detail and hasattr(detail, "text") else str(e)
        st.error(f"Failed to save app settings: {msg}")
        return False


def save_assistants_config(assistants_data: list[dict[str, Any]]) -> bool:
    """Send the list of assistants configuration to the backend."""
    try:
        resp = SESSION.post(f"{BACKEND_URL}/assistants", json=assistants_data, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        get_assistants_config.clear()
        return True
    except requests.exceptions.RequestException as e:
        detail = getattr(e, "response", None)
        try:
            msg = detail.json().get("detail", str(e)) if detail else str(e)
        except Exception:
            msg = detail.text if detail and hasattr(detail, "text") else str(e)
        st.error(f"Failed to save assistants configuration: {msg}")
        return False


def add_plugin_to_assistant_api(assistant_id: str, plugin_name: str) -> bool:
    """Request the backend to add a plugin to the specified assistant."""
    try:
        resp = SESSION.post(
            f"{BACKEND_URL}/assistants/{assistant_id}/add_plugin",
            params={"plugin_name": plugin_name},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        get_assistants_config.clear()
        return True
    except requests.exceptions.RequestException as e:
        detail = getattr(e, "response", None)
        try:
            error_message = detail.json().get("detail", "An unknown error occurred.") if detail else str(e)
        except Exception:
            error_message = detail.text if detail and hasattr(detail, "text") else str(e)
        st.error(f"Failed to add plugin '{plugin_name}': {error_message}")
        return False
    except Exception as e:
        st.error(f"An unknown error occurred while adding the plugin: {e}")
        return False


def remove_plugin_from_assistant_api(assistant_id: str, plugin_name: str) -> bool:
    """Request the backend to remove a plugin from the specified assistant."""
    try:
        resp = SESSION.post(
            f"{BACKEND_URL}/assistants/{assistant_id}/remove_plugin",
            params={"plugin_name": plugin_name},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        get_assistants_config.clear()
        return True
    except requests.exceptions.RequestException as e:
        detail = getattr(e, "response", None)
        try:
            error_message = detail.json().get("detail", "An unknown error occurred.") if detail else str(e)
        except Exception:
            error_message = detail.text if detail and hasattr(detail, "text") else str(e)
        st.error(f"Failed to remove plugin '{plugin_name}': {error_message}")
        return False
    except Exception as e:
        st.error(f"An unknown error occurred while removing the plugin: {e}")
        return False


def remove_plugin(plugin_name: str) -> bool:
    """Request the backend to delete a plugin."""
    try:
        resp = SESSION.post(
            f"{BACKEND_URL}/plugins/remove",
            json={"plugin_name": plugin_name},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        get_available_plugins.clear()
        return True
    except requests.exceptions.RequestException as e:
        detail = getattr(e, "response", None)
        try:
            msg = detail.json().get("detail", str(e)) if detail else str(e)
        except Exception:
            msg = detail.text if detail and hasattr(detail, "text") else str(e)
        st.error(f"Failed to delete plugin '{plugin_name}': {msg}")
        return False
    except Exception as e:
        st.error(f"An unknown error occurred while deleting the plugin: {e}")
        return False


def remove_assistant(assistant_id: str) -> bool:
    try:
        resp = SESSION.post(
            f"{BACKEND_URL}/assistants/remove_assistant",
            json={"assistant_id": assistant_id},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        get_assistants_config.clear()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to remove assistant: {e}")
        return False


# --- Logging API ---


@st.cache_data(ttl=2, show_spinner=False)
def get_logs(level: str | None = None, module: str | None = None, limit: int | None = None, search: str | None = None) -> list[dict[str, Any]]:
    """Get logs from the log manager for dashboard display."""
    try:
        resp = SESSION.post(
            f"{BACKEND_URL}/app/logs",
            json={"level": level, "module": module, "limit": limit, "search": search},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch logs: {e}")
        return []
    except Exception as e:
        st.error(f"An error occurred while processing logs: {e}")
        return []


def get_log_statistics() -> dict[str, Any]:
    """Get logging statistics for dashboard display."""
    try:
        resp = SESSION.get(f"{BACKEND_URL}/app/log_statistics", timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch log statistics: {e}")
    except Exception as e:
        st.error(f"An error occurred while processing log statistics: {e}")
    return {"total_logs": 0, "by_level": {}, "by_module": {}, "oldest_timestamp": None, "newest_timestamp": None}


def clear_all_logs() -> bool:
    """Clear all logs from the log manager."""
    try:
        resp = SESSION.post(f"{BACKEND_URL}/app/logs/clear", timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        get_logs.clear()
        return True
    except requests.exceptions.RequestException as e:
        detail = getattr(e, "response", None)
        try:
            msg = detail.json().get("detail", str(e)) if detail else str(e)
        except Exception:
            msg = detail.text if detail and hasattr(detail, "text") else str(e)
        st.error(f"Failed to clear logs: {msg}")
        return False
    except Exception as e:
        st.error(f"An unknown error occurred while clearing logs: {e}")
        return False
