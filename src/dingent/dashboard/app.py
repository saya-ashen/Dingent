import copy
import html
from typing import Any

import streamlit as st

from dingent.dashboard.api import (
    add_plugin_to_assistant_api,
    clear_all_logs,
    get_app_settings,
    get_assistants_config,
    get_available_plugins,
    get_log_statistics,
    get_logs,
    remove_plugin,
    remove_plugin_from_assistant_api,
    save_app_settings,
    save_assistants_config,
)
from dingent.dashboard.ui_components import bordered_container, inject_base_css, render_confirm_dialog

# --- Page Setup ---
st.set_page_config(page_title="Assistant Configuration Editor", page_icon="🤖", layout="wide")
inject_base_css()
st.title("Admin Dashboard")


# --- Helper Functions ---
def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, "", "None"):
        return default
    # Fix fatal runtime: isinstance doesn't accept union types; use a tuple.
    if isinstance(value, int | float):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "t", "yes", "y", "on")
    return default


def _to_str(value: Any) -> str:
    return "" if value is None else str(value)


def _status_level_from_text(text: str) -> str:
    """
    Map backend-reported status text to: ok | warn | error | unknown
    """
    if not text:
        return "unknown"
    t = str(text).strip().lower()
    ok_keys = ("ok", "healthy", "ready", "running", "active", "online", "up", "success")
    warn_keys = ("pending", "starting", "initializing", "init", "degraded", "slow", "busy")
    err_keys = ("error", "failed", "down", "crash", "unhealthy", "timeout", "offline")
    if any(k in t for k in ok_keys):
        return "ok"
    if any(k in t for k in warn_keys):
        return "warn"
    if any(k in t for k in err_keys):
        return "error"
    return "unknown"


def _build_status_badge(label: str, level: str, title: str | None = None) -> str:
    """
    Generate an HTML snippet for a status badge.
    level: ok | warn | error | disabled | unknown
    """
    safe_label = html.escape(label if label is not None else "")
    classes = f"status-badge status-{level}"
    title_attr = f' title="{html.escape(title)}"' if title else ""
    return f'<span class="{classes}"{title_attr}><span class="dot"></span>{safe_label}</span>'


def _effective_status_for_assistant(raw_status: Any, enabled: bool) -> tuple[str, str]:
    """
    Compute the display (level, label) based on enable state and original status.
    """
    if not enabled:
        return "disabled", "Disabled"
    text = _to_str(raw_status) or "Unknown"
    level = _status_level_from_text(text)
    # Make the label friendlier (retain original text)
    label_map = {
        "ok": "OK",
        "warn": "Warning",
        "error": "Error",
        "unknown": "Unknown",
    }
    # Supplement with the original status: e.g., "OK (running)"
    friendly = f"{label_map.get(level, 'Unknown')} ({text})"
    return level, friendly


def _effective_status_for_plugin(raw_status: Any, enabled: bool) -> tuple[str, str]:
    """
    Plugin display rule is same as assistant, disabled takes precedence.
    """
    if not enabled:
        return "disabled", "Disabled"
    text = _to_str(raw_status) or "Unknown"
    level = _status_level_from_text(text)
    label_map = {
        "ok": "OK",
        "warn": "Warning",
        "error": "Error",
        "unknown": "Unknown",
    }
    friendly = f"{label_map.get(level, 'Unknown')} ({text})"
    return level, friendly


def refresh_assistants_state():
    """Force refresh assistants configuration in session to reflect changes immediately after actions."""
    try:
        get_assistants_config.clear()
    except Exception:
        pass
    st.session_state.assistants_config = get_assistants_config()


def close_all_add_plugin_modes():
    """Close all expanded 'add plugin' modes to avoid lingering UI after operations."""
    for k in list(st.session_state.keys()):
        if k.endswith("_add_plugin_mode"):
            try:
                del st.session_state[k]
            except Exception:
                pass


# --- Init session states ---
if "app_settings" not in st.session_state:
    st.session_state.app_settings = get_app_settings()
if "assistants_config" not in st.session_state:
    st.session_state.assistants_config = get_assistants_config()

with st.sidebar:
    st.header("Actions")
    if st.button("🔄 Refresh", key="toolbar_refresh", help="Reload configuration from server", use_container_width=True):
        get_app_settings.clear()
        get_assistants_config.clear()
        get_available_plugins.clear()
        st.session_state.app_settings = get_app_settings()
        st.session_state.assistants_config = get_assistants_config()
        st.toast("Configuration refreshed!", icon="✅")
        st.rerun()

    save_clicked = st.button(
        "💾 Save all changes",
        key="toolbar_save",
        type="primary",
        help="Save all changes to the server",
        use_container_width=True,
    )

if not st.session_state.app_settings or st.session_state.assistants_config is None:
    st.warning("Failed to load complete configuration from the backend. Ensure the backend service is running, then click Refresh.")
    st.stop()

editable_settings = copy.deepcopy(st.session_state.app_settings)
editable_assistants = copy.deepcopy(st.session_state.assistants_config)

# --- UI Rendering ---
st.markdown('<div class="sticky-tabs-marker"></div>', unsafe_allow_html=True)
tab_assistants, tab_plugins, tab_other_settings, tab_logs = st.tabs(["🤖 Assistant Configuration", "🔌 Plugin Management", "⚙️ App Settings", "📋 System Logs"])

# Dialog state keys prefix
PREFIX_ADD = "dlg_add_plugin_"
PREFIX_REMOVE = "dlg_remove_plugin_"
PREFIX_DELETE = "dlg_delete_plugin_"

with tab_assistants:
    if not editable_assistants:
        st.info("There are currently no assistants to configure.")

    for i, assistant in enumerate(editable_assistants):
        name = assistant.get("name") or "Unnamed"
        assistant_id = assistant.get("id")
        enabled = _safe_bool(assistant.get("enabled"), default=False)
        status = assistant.get("status", "Unknown")

        with st.expander(f"{'✅' if enabled else '❌'} Assistant: {name}", expanded=True):
            st.subheader("Basic Settings")
            col1, col2, col3 = st.columns([3, 1, 2])
            with col1:
                assistant["name"] = st.text_input("Assistant Name", value=_to_str(assistant.get("name", "")), key=f"as_{i}_name")
            with col2:
                assistant["enabled"] = st.toggle("Enable this assistant", value=_safe_bool(assistant.get("enabled"), default=False), key=f"as_{i}_enabled")
            with col3:
                # Colored status badge instead of a gray disabled input
                lvl, label = _effective_status_for_assistant(status, _safe_bool(assistant.get("enabled"), False))
                badge_html = _build_status_badge(label, lvl, title=_to_str(status))
                st.markdown(f"Service Status: {badge_html}", unsafe_allow_html=True)

            assistant["description"] = st.text_area("Assistant Description", value=_to_str(assistant.get("description", "")), key=f"as_{i}_desc")
            st.markdown("---")
            st.subheader("🔌 Plugin Configuration")

            # --- Add New Plugin UI ---
            add_plugin_key = f"as_{i}_add_plugin_mode"
            cols_add_plugin = st.columns([3, 1])
            with cols_add_plugin[1]:
                if st.button("➕ Add Plugin", key=f"as_{i}_add_plugin"):
                    st.session_state[add_plugin_key] = True
            if st.session_state.get(add_plugin_key):
                with bordered_container():
                    all_plugins = get_available_plugins() or []
                    current_plugin_names = {p.get("name") for p in assistant.get("plugins", [])}
                    available_to_add = [p for p in all_plugins if p.get("name") not in current_plugin_names]
                    if not available_to_add:
                        st.warning("No other plugins available to add.")
                        if st.button("Close", key=f"as_{i}_close_add"):
                            del st.session_state[add_plugin_key]
                            st.rerun()
                    else:
                        st.markdown("Select a plugin to add:")
                        col_select, col_confirm, col_cancel = st.columns([2, 1, 1])
                        with col_select:
                            selected_plugin_name = st.selectbox(
                                "Available Plugins",
                                options=[p["name"] for p in available_to_add],
                                key=f"as_{i}_select_plugin",
                                label_visibility="collapsed",
                            )
                        with col_confirm:
                            if st.button("Confirm Add", key=f"as_{i}_confirm_add", type="primary"):
                                if not assistant_id:
                                    st.error("Cannot add plugin: Assistant ID not found. Please refresh the page.")
                                elif not selected_plugin_name:
                                    st.warning("Please select a plugin.")
                                else:
                                    dlg_key = f"{PREFIX_ADD}{assistant_id}"
                                    st.session_state[dlg_key] = {
                                        "open": True,
                                        "result": None,
                                        "payload": {
                                            "assistant_id": assistant_id,
                                            "assistant_name": name,
                                            "plugin_name": selected_plugin_name,
                                        },
                                    }
                                    st.rerun()
                        with col_cancel:
                            if st.button("Cancel", key=f"as_{i}_cancel_add"):
                                del st.session_state[add_plugin_key]
                                st.rerun()

            plugins = assistant.get("plugins", [])
            if not plugins:
                st.caption("This assistant currently has no configured plugins.")

            for j, plugin in enumerate(plugins):
                with bordered_container():
                    p_name = plugin.get("name") or f"plugin_{j}"
                    p_status = plugin.get("status", "N/A")
                    p_enabled = _safe_bool(plugin.get("enabled"), default=False)

                    colp1, colp2, colp3 = st.columns([5, 2, 1])
                    with colp1:
                        st.markdown(f"Plugin: `{_to_str(p_name)}`")
                        lvl, label = _effective_status_for_plugin(p_status, p_enabled)
                        badge = _build_status_badge(label, lvl, title=_to_str(p_status))
                        st.markdown(f"Status: {badge}", unsafe_allow_html=True)
                    with colp2:
                        plugin["enabled"] = st.toggle(
                            "Enable plugin",
                            value=p_enabled,
                            key=f"as_{i}_pl_{j}_enabled",
                        )
                        # If user toggles the switch, update badge state immediately
                        p_enabled = plugin["enabled"]
                    with colp3:
                        if st.button("🗑️", key=f"as_{i}_pl_{j}_remove", help=f"Remove {p_name} from {name}"):
                            dlg_key = f"{PREFIX_REMOVE}{assistant_id}_{p_name}"
                            st.session_state[dlg_key] = {
                                "open": True,
                                "result": None,
                                "payload": {"assistant_id": assistant_id, "assistant_name": name, "plugin_name": p_name},
                            }
                            st.rerun()

                    # Configuration area
                    config_items = plugin.get("config")
                    if isinstance(config_items, list) and config_items:
                        st.markdown("User Configuration:")
                        for config_item in config_items:
                            item_name = config_item.get("name")
                            if not item_name:
                                continue
                            item_type = config_item.get("type", "string")
                            is_required = config_item.get("required", False)
                            is_secret = config_item.get("secret", False)
                            description = config_item.get("description", f"Set {item_name}")
                            default_value = config_item.get("default")
                            current_value = config_item.get("value")
                            label_txt = f"{item_name}{' (Required)' if is_required else ''}"
                            if item_type == "integer":
                                try:
                                    display_value = current_value if current_value is not None else default_value
                                    display_value = int(display_value) if display_value is not None else 0
                                except (ValueError, TypeError):
                                    display_value = int(default_value) if default_value is not None else 0
                                new_val = st.number_input(
                                    label_txt,
                                    value=display_value,
                                    step=1,
                                    help=description,
                                    key=f"as_{i}_pl_{j}_cfg_{item_name}",
                                )
                                config_item["value"] = new_val
                            else:
                                display_value = current_value if current_value is not None else default_value
                                new_val = st.text_input(
                                    label_txt,
                                    value=_to_str(display_value),
                                    type="password" if is_secret else "default",
                                    help=description,
                                    key=f"as_{i}_pl_{j}_cfg_{item_name}",
                                )
                                config_item["value"] = new_val

                    tools = plugin.get("tools") or []
                    if isinstance(tools, list) and tools:
                        st.markdown("Tools:")
                        for k, tool in enumerate(tools):
                            tool_name = tool.get("name") or f"tool_{k}"
                            tool_col1, tool_col2 = st.columns([3, 1])
                            with tool_col2:
                                is_enabled = st.toggle(
                                    "Enable tool",
                                    value=_safe_bool(tool.get("enabled"), default=False),
                                    key=f"as_{i}_pl_{j}_tool_{k}_enabled",
                                )
                                tool["enabled"] = is_enabled
                            with tool_col1:
                                st.markdown(f"`{_to_str(tool_name)}`")
                                if is_enabled and tool.get("description"):
                                    st.caption(_to_str(tool.get("description")))


with tab_plugins:
    st.subheader("Install New Plugin (Placeholder)")
    with bordered_container():
        st.text_input("Install from Git Repository", placeholder="https://github.com/user/my-agent-plugin.git")
        st.file_uploader("Or upload plugin (.zip)")
        if st.button("Install Plugin", key="install_plugin_btn"):
            st.info("✨ Feature coming soon: installing plugins via the UI is under development.")
    st.markdown("---")
    st.subheader("All Available Plugins")
    st.caption("This lists all plugins successfully loaded from the plugin directory and their metadata.")
    available_plugins = get_available_plugins()
    if available_plugins is None:
        st.error("Unable to fetch the plugin list from the backend.")
    elif not available_plugins:
        st.info("No available plugins found.")
    else:
        for p_manifest in available_plugins:
            p_name = p_manifest.get("name", "Unknown Plugin")
            with st.expander(f"{p_name} (v{p_manifest.get('version', 'N/A')})"):
                st.markdown(f"> {p_manifest.get('description', 'No description provided.')}")
                st.markdown("---")
                cols_info, cols_action = st.columns([3, 1])
                with cols_info:
                    st.markdown(f"Spec Version: `{p_manifest.get('spec_version', 'N/A')}`")
                    mode = p_manifest.get("execution", {}).get("mode", "N/A")
                    st.markdown(f"Execution Mode: `{mode}`")
                with cols_action:
                    if st.button("🗑️ Delete", key=f"delete_btn_{p_name}", type="secondary"):
                        dlg_key = f"{PREFIX_DELETE}{p_name}"
                        st.session_state[dlg_key] = {
                            "open": True,
                            "result": None,
                            "payload": {"plugin_name": p_name},
                        }
                        st.rerun()
                dependencies = p_manifest.get("dependencies")
                if isinstance(dependencies, list) and dependencies:
                    st.markdown("Dependencies:")
                    st.code("\n".join(dependencies), language="text")

with tab_other_settings:
    st.subheader("LLM Provider Settings")
    llm_config = editable_settings.get("llm", {})
    llm_config["model"] = st.text_input("Model Name", value=_to_str(llm_config.get("model")))
    llm_config["base_url"] = st.text_input("API Base URL", value=_to_str(llm_config.get("base_url")))
    llm_config["provider"] = st.text_input(
        "Provider",
        value=_to_str(llm_config.get("provider")),
        help="For example: 'openai', 'anthropic', etc.",
    )
    llm_config["api_key"] = st.text_input(
        "API Key",
        value=_to_str(llm_config.get("api_key")),
        type="password",
        help="If using providers like OpenAI, enter the API key here.",
    )
    st.markdown("---")
    st.subheader("General Settings")
    editable_settings["default_assistant"] = st.text_input(
        "Default Assistant Name",
        value=_to_str(editable_settings.get("default_assistant")),
        help="The assistant name used by default when the user does not specify one.",
    )

with tab_logs:
    st.subheader("System Logs")

    # Log statistics section
    col_stats, col_actions = st.columns([2, 1])

    with col_stats:
        st.markdown("**Log Statistics**")
        log_stats = get_log_statistics()

        if log_stats["total_logs"] > 0:
            # Display basic stats
            st.metric("Total Logs", log_stats["total_logs"])

            # Display by level
            if log_stats["by_level"]:
                st.markdown("**By Level:**")
                level_cols = st.columns(len(log_stats["by_level"]))
                for i, (level, count) in enumerate(log_stats["by_level"].items()):
                    with level_cols[i]:
                        st.metric(level, count)
        else:
            st.info("No logs available")

    with col_actions:
        st.markdown("**Actions**")
        if st.button("🔄 Refresh Logs", use_container_width=True):
            get_logs.clear()
            st.rerun()

        if st.button("🗑️ Clear All Logs", type="secondary", use_container_width=True):
            if clear_all_logs():
                st.toast("All logs cleared", icon="✅")
                st.rerun()

    st.markdown("---")

    # Log filtering section
    st.markdown("**Filter Logs**")
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

    with filter_col1:
        level_filter = st.selectbox("Level", options=["All", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], index=0)

    with filter_col2:
        module_filter = st.text_input("Module", placeholder="e.g., config_manager")

    with filter_col3:
        search_filter = st.text_input("Search", placeholder="Search in message...")

    with filter_col4:
        limit_filter = st.number_input("Limit", min_value=10, max_value=500, value=100, step=10)

    # Apply filters
    level_param = None if level_filter == "All" else level_filter
    module_param = module_filter if module_filter.strip() else None
    search_param = search_filter if search_filter.strip() else None

    # Get and display logs
    logs = get_logs(level=level_param, module=module_param, limit=int(limit_filter), search=search_param)

    if logs:
        st.markdown(f"**Showing {len(logs)} logs**")

        # Display logs in an expandable format
        for log in logs:
            timestamp = log.get("timestamp", "Unknown")
            level = log.get("level", "UNKNOWN")
            message = log.get("message", "")
            module = log.get("module", "unknown")
            function = log.get("function", "unknown")

            # Color code by level
            level_colors = {"DEBUG": "#808080", "INFO": "#0066CC", "WARNING": "#FF8C00", "ERROR": "#FF4444", "CRITICAL": "#CC0000"}
            color = level_colors.get(level, "#000000")

            with st.expander(f"[{timestamp[:19]}] **{level}** in `{module}.{function}` - {message[:100]}", expanded=False):
                st.markdown(f"**Level:** <span style='color: {color}; font-weight: bold;'>{level}</span>", unsafe_allow_html=True)
                st.markdown(f"**Timestamp:** {timestamp}")
                st.markdown(f"**Module:** `{module}`")
                st.markdown(f"**Function:** `{function}`")
                st.markdown("**Message:**")
                st.code(message, language="text")

                # Show context if available
                context = log.get("context")
                if context and context != {}:
                    st.markdown("**Context:**")
                    st.json(context)

                # Show correlation ID if available
                correlation_id = log.get("correlation_id")
                if correlation_id:
                    st.markdown(f"**Correlation ID:** `{correlation_id}`")
    else:
        st.info("No logs match the current filters.")

# --- Save Action ---
if save_clicked:
    with st.spinner("Saving configuration..."):
        for a in editable_assistants:
            a["enabled"] = _safe_bool(a.get("enabled"), default=False)
            for p in a.get("plugins", []):
                p["enabled"] = _safe_bool(p.get("enabled"), default=False)
                for t in p.get("tools", []):
                    t["enabled"] = _safe_bool(t.get("enabled"), default=False)
        settings_ok = save_app_settings(editable_settings)
        assistants_ok = save_assistants_config(editable_assistants)
        if settings_ok and assistants_ok:
            st.session_state.app_settings = get_app_settings()
            st.session_state.assistants_config = get_assistants_config()
            st.toast("✅ All configuration saved and refreshed successfully!")
            st.rerun()
        else:
            st.error("❌ Save failed. Please check the error messages above and try again.")

# --- Dialog Dispatcher ---
for key in list(st.session_state.keys()):
    if key.startswith(PREFIX_ADD):
        state = st.session_state.get(key) or {}
        if state.get("open"):
            payload = state.get("payload", {})
            assistant_name = payload.get("assistant_name", "")
            plugin_name = payload.get("plugin_name", "")
            render_confirm_dialog(
                key,
                "Confirm Add Plugin",
                f"Are you sure you want to add plugin '{plugin_name}' to assistant '{assistant_name}'?",
                confirm_text="Confirm Add",
                cancel_text="Cancel",
            )
        elif state.get("result") in ("confirmed", "cancelled"):
            payload = (state.get("payload") or {}).copy()
            confirmed = state["result"] == "confirmed"
            st.session_state.pop(key, None)
            if confirmed:
                with st.spinner("Adding plugin..."):
                    ok = add_plugin_to_assistant_api(payload["assistant_id"], payload["plugin_name"])
                if ok:
                    st.toast(f"Added plugin '{payload['plugin_name']}' to {payload['assistant_name']}", icon="✅")
                    refresh_assistants_state()
                    close_all_add_plugin_modes()
                    st.rerun()

    if key.startswith(PREFIX_REMOVE):
        state = st.session_state.get(key) or {}
        if state.get("open"):
            payload = state.get("payload", {})
            assistant_name = payload.get("assistant_name", "")
            plugin_name = payload.get("plugin_name", "")
            render_confirm_dialog(
                key,
                "Confirm Remove Plugin",
                f"Are you sure you want to remove plugin '{plugin_name}' from assistant '{assistant_name}'?",
                confirm_text="Confirm Remove",
                cancel_text="Cancel",
            )
        elif state.get("result") in ("confirmed", "cancelled"):
            payload = (state.get("payload") or {}).copy()
            confirmed = state["result"] == "confirmed"
            st.session_state.pop(key, None)
            if confirmed:
                with st.spinner("Removing plugin..."):
                    ok = remove_plugin_from_assistant_api(payload["assistant_id"], payload["plugin_name"])
                if ok:
                    st.toast(f"Plugin '{payload['plugin_name']}' removed from {payload['assistant_name']}", icon="✅")
                    refresh_assistants_state()
                    st.rerun()

    if key.startswith(PREFIX_DELETE):
        state = st.session_state.get(key) or {}
        if state.get("open"):
            payload = state.get("payload", {})
            plugin_name = payload.get("plugin_name", "")
            render_confirm_dialog(
                key,
                "Confirm Delete Plugin",
                f"Are you sure you want to delete plugin '{plugin_name}'? This may affect assistants that reference this plugin.",
                confirm_text="Confirm Delete",
                cancel_text="Cancel",
            )
        elif state.get("result") in ("confirmed", "cancelled"):
            payload = (state.get("payload") or {}).copy()
            confirmed = state["result"] == "confirmed"
            st.session_state.pop(key, None)
            if confirmed:
                with st.spinner("Deleting plugin..."):
                    ok = remove_plugin(payload["plugin_name"])
                if ok:
                    st.toast(f"Plugin '{payload['plugin_name']}' deleted", icon="✅")
                    refresh_assistants_state()
                    st.rerun()
