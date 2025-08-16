import copy
import inspect
import os
from typing import Any

import requests
import streamlit as st

# --- Configuration ---
BACKEND_URL = os.getenv("ASSISTANTS_ADMIN_BACKEND_URL", "http://127.0.0.1:2024/admin")
HTTP_TIMEOUT = 10  # seconds
SESSION = requests.Session()


MARGINS = {
    "top": "2.875rem",
    "bottom": "0",
}


# --- Page Setup ---
st.set_page_config(page_title="助手配置编辑器", page_icon="🤖", layout="wide")

st.title("Admin Dashbord")


# --- Helper Functions ---


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, "", "None"):
        return default
    if isinstance(value, int | float):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "t", "yes", "y", "on")
    return default


def _to_str(value: Any) -> str:
    return "" if value is None else str(value)


def _bordered_container():
    """兼容旧版本 Streamlit 不支持 border 参数的情况。"""
    try:
        sig = inspect.signature(st.container)
        if "border" in sig.parameters:
            return st.container(border=True)
    except Exception:
        pass
    return st.container()


@st.cache_data(ttl=5, show_spinner=False)
def get_current_config() -> dict[str, Any] | None:
    """从后端获取当前配置"""
    try:
        resp = SESSION.get(f"{BACKEND_URL}/config/app", timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        if getattr(e, "response", None) is not None:
            try:
                detail = e.response.json()
            except Exception:
                detail = getattr(e.response, "text", "")
            st.error(f"无法连接到后端或获取配置: {e}\n后端返回: {detail}")
        else:
            st.error(f"无法连接到后端或获取配置: {e}")
        return None
    except Exception as e:
        st.error(f"处理配置时发生未知错误: {e}")
        return None


def save_new_config(config_data: dict[str, Any]) -> bool:
    """将新配置发送到后端"""
    try:
        resp = SESSION.post(f"{BACKEND_URL}/config/app", json=config_data, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        # 清理配置缓存
        get_current_config.clear()
        return True
    except requests.exceptions.RequestException as e:
        msg = f"保存配置失败: {e}"
        backend_detail = ""
        if getattr(e, "response", None) is not None:
            try:
                backend_detail = e.response.json()
            except Exception:
                backend_detail = getattr(e.response, "text", "")
        st.error(msg)
        if backend_detail:
            st.error(f"后端返回信息: {backend_detail}")
        return False
    except Exception as e:
        st.error(f"保存时发生未知错误: {e}")
        return False


# --- Main Application Logic ---

# 加载配置到 session_state
if "config" not in st.session_state:
    st.session_state.config = get_current_config()

# 顶部右上角“悬浮”工具栏（刷新 + 保存）
save_clicked = False

with st.sidebar:
    st.header("操作")  # 可以加个标题
    if st.button("🔄 刷新", key="toolbar_refresh", help="从服务器重新获取配置", use_container_width=True):
        get_current_config.clear()
        st.session_state.config = get_current_config()
        if st.session_state.config:
            st.success("配置已刷新！")
        else:
            st.warning("未能加载配置。")
        st.rerun()
    save_clicked = st.button("💾 保存", key="toolbar_save", type="primary", help="保存所有更改到服务器", use_container_width=True)


# 如果首次加载失败
if not st.session_state.config:
    st.warning("未能从后端加载配置。请确保后端服务正在运行，然后点击右上角“刷新”。")
    st.stop()

# 使用深拷贝作为“工作副本”
editable_config: dict[str, Any] = copy.deepcopy(st.session_state.config)

# --- 表单外渲染（按钮在上方工具栏，主体内容正常滚动） ---

st.markdown('<div class="sticky-tabs-marker"></div>', unsafe_allow_html=True)

# 创建 Tabs
tab_assistants, tab_other_settings = st.tabs(["🤖 助手配置", "⚙️ 其他设置 (占位)"])

# 将所有助手相关的UI放入第一个 Tab
with tab_assistants:
    assistants = editable_config.get("assistants", [])
    if not isinstance(assistants, list):
        st.error("配置格式错误：'assistants' 应为列表。")
        assistants = []

    if not assistants:
        st.info("当前没有可配置的助手。")

    for i, assistant in enumerate(assistants):
        if not isinstance(assistant, dict):
            continue

        name = assistant.get("name") or "Unnamed"
        enabled = _safe_bool(assistant.get("enabled"), default=False)
        status = assistant.get("status", "Unknown")

        with st.expander(f"{'✅' if enabled else '❌'} 助手: {name}", expanded=True):
            # --- Assistant Level Settings ---
            st.subheader("基本设置")

            col1, col2 = st.columns([3, 1])
            with col1:
                assistant["name"] = st.text_input(
                    "助手名称 (Name)",
                    value=_to_str(assistant.get("name", "")),
                    key=f"as_{i}_name",
                )
            with col2:
                assistant["enabled"] = st.toggle(
                    "启用此助手",
                    value=_safe_bool(assistant.get("enabled"), default=False),
                    key=f"as_{i}_enabled",
                )

            assistant["description"] = st.text_area(
                "助手描述 (Description)",
                value=_to_str(assistant.get("description", "")),
                key=f"as_{i}_desc",
            )

            st.text_input(
                "服务状态 (Status)",
                value=_to_str(status),
                key=f"as_{i}_status_display",
                disabled=True,
            )

            st.markdown("---")

            # --- Plugins Level Settings ---
            st.subheader("🔌 插件配置")
            plugins = assistant.get("plugins", [])
            if not plugins:
                st.caption("此助手没有配置插件。")

            if not isinstance(plugins, list):
                st.warning("插件配置格式错误：'plugins' 应为列表。已跳过此助手的插件渲染。")
                plugins = []

            for j, plugin in enumerate(plugins):
                if not isinstance(plugin, dict):
                    continue

                with _bordered_container():
                    p_name = plugin.get("name") or f"plugin_{j}"
                    p_status = plugin.get("status", "N/A")

                    colp1, colp2 = st.columns([3, 1])
                    with colp1:
                        st.markdown(f"**插件: `{_to_str(p_name)}`**")
                        st.caption(f"Status: {_to_str(p_status)}")
                    with colp2:
                        plugin["enabled"] = st.toggle(
                            "启用插件",
                            value=_safe_bool(plugin.get("enabled"), default=False),
                            key=f"as_{i}_pl_{j}_enabled",
                        )

                    # vvvvvvvvvv MODIFIED CODE BLOCK vvvvvvvvvv
                    # --- Plugin User Config (from new data structure) ---
                    config_items = plugin.get("config")
                    if isinstance(config_items, list) and config_items:
                        st.markdown("**🔑 用户配置:**")

                        for config_item in config_items:
                            if not isinstance(config_item, dict):
                                continue

                            # Extract details from the config item
                            item_name = config_item.get("name")
                            if not item_name:
                                continue

                            item_type = config_item.get("type", "string")
                            is_required = config_item.get("required", False)
                            is_secret = config_item.get("secret", False)
                            description = config_item.get("description", f"设置 {item_name}")
                            default_value = config_item.get("default")
                            current_value = config_item.get("value")

                            # Build the UI label
                            label = f"`{item_name}`"
                            if is_required:
                                label += " (必填)"

                            # Render the appropriate widget based on type
                            if item_type == "integer":
                                try:
                                    # Use current value if set, otherwise default, otherwise 0
                                    display_value = current_value if current_value is not None else default_value
                                    display_value = int(display_value) if display_value is not None else 0
                                except (ValueError, TypeError):
                                    display_value = int(default_value) if default_value is not None else 0

                                new_val = st.number_input(label, value=display_value, step=1, help=description, key=f"as_{i}_pl_{j}_cfg_{item_name}")
                                # IMPORTANT: Update the 'value' key in the config_item dictionary
                                config_item["value"] = new_val

                            else:  # Default to string type
                                # Use current value if set, otherwise default
                                display_value = current_value if current_value is not None else default_value
                                new_val = st.text_input(
                                    label, value=_to_str(display_value), type="password" if is_secret else "default", help=description, key=f"as_{i}_pl_{j}_cfg_{item_name}"
                                )
                                # IMPORTANT: Update the 'value' key in the config_item dictionary
                                config_item["value"] = new_val

                    # --- Tools Level Settings ---
                    tools = plugin.get("tools") or []
                    if isinstance(tools, list) and tools:
                        st.markdown("**🔧 工具列表:**")
                        for k, tool in enumerate(tools):
                            if not isinstance(tool, dict):
                                continue
                            tool_name = tool.get("name") or f"tool_{k}"
                            tool_desc = tool.get("description") or ""
                            tool_col1, tool_col2 = st.columns([3, 1])
                            with tool_col1:
                                st.markdown(f"`{_to_str(tool_name)}`")
                                if tool_desc:
                                    st.caption(_to_str(tool_desc))
                            with tool_col2:
                                tool["enabled"] = st.toggle(
                                    "启用工具",
                                    value=_safe_bool(tool.get("enabled"), default=False),
                                    key=f"as_{i}_pl_{j}_tool_{k}_enabled",
                                )
                    # ^^^^^^^^^^^ END OF MODIFIED CODE BLOCK ^^^^^^^^^^^^


# 其他 Tab 的内容
with tab_other_settings:
    st.info("这里可以放置其他的全局配置项，例如通用设置、模型提供商密钥等。")
    st.warning("此功能区域正在开发中...")
# --- 保存动作 ---
if save_clicked:
    with st.spinner("正在保存..."):
        # 提交前规整布尔与结构，防止后端 schema 校验失败
        try:
            for a in editable_config.get("assistants", []) or []:
                a["enabled"] = _safe_bool(a.get("enabled"), default=False)
                for p in a.get("plugins", []) or []:
                    p["enabled"] = _safe_bool(p.get("enabled"), default=False)
                    for t in p.get("tools", []) or []:
                        t["enabled"] = _safe_bool(t.get("enabled"), default=False)
                    if "config" in p and not isinstance(p["config"], list):
                        p["config"] = []  # Ensure config is a list
        except Exception as norm_err:
            st.error(f"提交前数据规整失败: {norm_err}")
        else:
            if save_new_config(editable_config):
                # 保存成功后：重新从服务器拉取最新配置，保证界面与后端状态同步
                fresh = get_current_config()
                if fresh:
                    st.session_state.config = fresh
                else:
                    st.session_state.config = editable_config
                st.success("✅ 配置已成功保存并已从服务器刷新！")
                st.rerun()
            else:
                st.error("❌ 保存失败，请检查错误信息并重试。")
