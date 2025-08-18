import os
from typing import Any

import requests
import streamlit as st

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
