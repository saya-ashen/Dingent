import os
from typing import Any

import requests
import streamlit as st

# --- Configuration ---
BACKEND_URL = os.getenv("DING_BACKEND_ADMIN_URL", "http://127.0.0.1:2024")
HTTP_TIMEOUT = 120  # seconds
SESSION = requests.Session()


@st.cache_data(ttl=5, show_spinner="加载应用设置...")
def get_app_settings() -> dict[str, Any] | None:
    """从后端获取核心应用配置。"""
    try:
        resp = SESSION.get(f"{BACKEND_URL}/config/settings", timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"无法获取应用设置: {e}")
        return None
    except Exception as e:
        st.error(f"处理应用设置时发生错误: {e}")
        return None


@st.cache_data(ttl=5, show_spinner="加载助手配置...")
def get_assistants_config() -> list[dict[str, Any]] | None:
    """从后端获取助手配置列表。"""
    try:
        resp = SESSION.get(f"{BACKEND_URL}/assistants", timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"无法获取助手配置: {e}")
        return None
    except Exception as e:
        st.error(f"处理助手配置时发生错误: {e}")
        return None


@st.cache_data(ttl=30, show_spinner="正在加载可用插件列表...")
def get_available_plugins() -> list[dict[str, Any]] | None:
    """从后端获取所有可用的插件清单。"""
    try:
        resp = SESSION.get(f"{BACKEND_URL}/plugins/list", timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"无法获取可用插件列表: {e}")
        return None
    except Exception as e:
        st.error(f"处理插件列表时发生未知错误: {e}")
        return None


def save_app_settings(settings_data: dict[str, Any]) -> bool:
    """将核心应用配置发送到后端。"""
    try:
        resp = SESSION.post(f"{BACKEND_URL}/config/settings", json=settings_data, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        get_app_settings.clear()
        return True
    except requests.exceptions.RequestException as e:
        # 尝试从响应体中提取更可读的错误信息
        detail = getattr(e, "response", None)
        try:
            msg = detail.json().get("detail", str(e)) if detail else str(e)
        except Exception:
            msg = detail.text if detail and hasattr(detail, "text") else str(e)
        st.error(f"保存应用设置失败: {msg}")
        return False


def save_assistants_config(assistants_data: list[dict[str, Any]]) -> bool:
    """将助手配置列表发送到后端。"""
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
        st.error(f"保存助手配置失败: {msg}")
        return False


def add_plugin_to_assistant_api(assistant_id: str, plugin_name: str) -> bool:
    """请求后端将一个插件添加到指定的助手中。"""
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
        st.error(f"添加插件 '{plugin_name}' 失败: {error_message}")
        return False
    except Exception as e:
        st.error(f"处理添加插件时发生未知错误: {e}")
        return False


def remove_plugin_from_assistant_api(assistant_id: str, plugin_name: str) -> bool:
    """请求后端从指定的助手中移除一个插件。"""
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
        st.error(f"移除插件 '{plugin_name}' 失败: {error_message}")
        return False
    except Exception as e:
        st.error(f"处理移除插件时发生未知错误: {e}")
        return False


def remove_plugin(plugin_name: str) -> bool:
    """请求后端删除一个插件。"""
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
        st.error(f"删除插件 '{plugin_name}' 失败: {msg}")
        return False
    except Exception as e:
        st.error(f"处理插件删除时发生未知错误: {e}")
        return False
