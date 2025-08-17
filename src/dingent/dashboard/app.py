import copy
import html
from typing import Any

import streamlit as st

from dingent.dashboard.api import (
    add_plugin_to_assistant_api,
    get_app_settings,
    get_assistants_config,
    get_available_plugins,
    remove_plugin,
    remove_plugin_from_assistant_api,
    save_app_settings,
    save_assistants_config,
)
from dingent.dashboard.ui_components import bordered_container, inject_base_css, render_confirm_dialog

# --- Page Setup ---
st.set_page_config(page_title="助手配置编辑器", page_icon="🤖", layout="wide")
inject_base_css()
st.title("Admin Dashboard")


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


def _status_level_from_text(text: str) -> str:
    """
    将后端返回的状态文本映射到: ok | warn | error | unknown
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
    生成一个状态徽章的 HTML 片段。
    level: ok | warn | error | disabled | unknown
    """
    safe_label = html.escape(label if label is not None else "")
    classes = f"status-badge status-{level}"
    title_attr = f' title="{html.escape(title)}"' if title else ""
    return f'<span class="{classes}"{title_attr}><span class="dot"></span>{safe_label}</span>'


def _effective_status_for_assistant(raw_status: Any, enabled: bool) -> tuple[str, str]:
    """
    根据启用状态和原始状态计算最终显示用的 (level, label)。
    """
    if not enabled:
        return "disabled", "禁用"
    text = _to_str(raw_status) or "Unknown"
    level = _status_level_from_text(text)
    # 让标签更友好一些（保留原始文本）
    label_map = {
        "ok": "正常",
        "warn": "注意",
        "error": "错误",
        "unknown": "未知",
    }
    # 用原始状态补充：例如 “正常 (running)”
    friendly = f"{label_map.get(level, '未知')} ({text})"
    return level, friendly


def _effective_status_for_plugin(raw_status: Any, enabled: bool) -> tuple[str, str]:
    """
    插件显示规则与助手一致，禁用优先生效。
    """
    if not enabled:
        return "disabled", "禁用"
    text = _to_str(raw_status) or "Unknown"
    level = _status_level_from_text(text)
    label_map = {
        "ok": "正常",
        "warn": "注意",
        "error": "错误",
        "unknown": "未知",
    }
    friendly = f"{label_map.get(level, '未知')} ({text})"
    return level, friendly


def refresh_assistants_state():
    """强制刷新会话中的助手配置，供操作成功后立即反映。"""
    try:
        get_assistants_config.clear()
    except Exception:
        pass
    st.session_state.assistants_config = get_assistants_config()


def close_all_add_plugin_modes():
    """关闭所有 '添加插件' 的展开态，避免操作完成后仍然停留。"""
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
    st.header("操作")
    if st.button("🔄 刷新", key="toolbar_refresh", help="从服务器重新获取配置", use_container_width=True):
        get_app_settings.clear()
        get_assistants_config.clear()
        get_available_plugins.clear()
        st.session_state.app_settings = get_app_settings()
        st.session_state.assistants_config = get_assistants_config()
        st.toast("配置已刷新！", icon="✅")
        st.rerun()

    save_clicked = st.button(
        "💾 保存所有更改",
        key="toolbar_save",
        type="primary",
        help="保存所有更改到服务器",
        use_container_width=True,
    )

if not st.session_state.app_settings or st.session_state.assistants_config is None:
    st.warning("未能从后端加载完整配置。请确保后端服务正在运行，然后点击刷新。")
    st.stop()

editable_settings = copy.deepcopy(st.session_state.app_settings)
editable_assistants = copy.deepcopy(st.session_state.assistants_config)

# --- UI Rendering ---
st.markdown('<div class="sticky-tabs-marker"></div>', unsafe_allow_html=True)
tab_assistants, tab_plugins, tab_other_settings = st.tabs(["🤖 助手配置", "🔌 插件管理", "⚙️ 应用设置"])

# Dialog state keys prefix
PREFIX_ADD = "dlg_add_plugin_"
PREFIX_REMOVE = "dlg_remove_plugin_"
PREFIX_DELETE = "dlg_delete_plugin_"

with tab_assistants:
    if not editable_assistants:
        st.info("当前没有可配置的助手。")

    for i, assistant in enumerate(editable_assistants):
        name = assistant.get("name") or "Unnamed"
        assistant_id = assistant.get("id")
        enabled = _safe_bool(assistant.get("enabled"), default=False)
        status = assistant.get("status", "Unknown")

        with st.expander(f"{'✅' if enabled else '❌'} 助手: {name}", expanded=True):
            st.subheader("基本设置")
            col1, col2, col3 = st.columns([3, 1, 2])
            with col1:
                assistant["name"] = st.text_input("助手名称 (Name)", value=_to_str(assistant.get("name", "")), key=f"as_{i}_name")
            with col2:
                assistant["enabled"] = st.toggle("启用此助手", value=_safe_bool(assistant.get("enabled"), default=False), key=f"as_{i}_enabled")
            with col3:
                # 彩色状态徽章替代灰色禁用输入框
                lvl, label = _effective_status_for_assistant(status, _safe_bool(assistant.get("enabled"), False))
                badge_html = _build_status_badge(label, lvl, title=_to_str(status))
                st.markdown(f"服务状态: {badge_html}", unsafe_allow_html=True)

            assistant["description"] = st.text_area("助手描述 (Description)", value=_to_str(assistant.get("description", "")), key=f"as_{i}_desc")
            st.markdown("---")
            st.subheader("🔌 插件配置")

            # --- Add New Plugin UI ---
            add_plugin_key = f"as_{i}_add_plugin_mode"
            cols_add_plugin = st.columns([3, 1])
            with cols_add_plugin[1]:
                if st.button("➕ 添加插件", key=f"as_{i}_add_plugin"):
                    st.session_state[add_plugin_key] = True
            if st.session_state.get(add_plugin_key):
                with bordered_container():
                    all_plugins = get_available_plugins() or []
                    current_plugin_names = {p.get("name") for p in assistant.get("plugins", [])}
                    available_to_add = [p for p in all_plugins if p.get("name") not in current_plugin_names]
                    if not available_to_add:
                        st.warning("没有其他可用的插件可以添加。")
                        if st.button("关闭", key=f"as_{i}_close_add"):
                            del st.session_state[add_plugin_key]
                            st.rerun()
                    else:
                        st.markdown("选择要添加的插件:")
                        col_select, col_confirm, col_cancel = st.columns([2, 1, 1])
                        with col_select:
                            selected_plugin_name = st.selectbox(
                                "可用插件",
                                options=[p["name"] for p in available_to_add],
                                key=f"as_{i}_select_plugin",
                                label_visibility="collapsed",
                            )
                        with col_confirm:
                            if st.button("确认添加", key=f"as_{i}_confirm_add", type="primary"):
                                if not assistant_id:
                                    st.error("无法添加插件：助手 ID 未找到。请刷新页面。")
                                elif not selected_plugin_name:
                                    st.warning("请选择一个插件。")
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
                            if st.button("取消", key=f"as_{i}_cancel_add"):
                                del st.session_state[add_plugin_key]
                                st.rerun()

            plugins = assistant.get("plugins", [])
            if not plugins:
                st.caption("此助手当前没有配置插件。")

            for j, plugin in enumerate(plugins):
                with bordered_container():
                    p_name = plugin.get("name") or f"plugin_{j}"
                    p_status = plugin.get("status", "N/A")
                    p_enabled = _safe_bool(plugin.get("enabled"), default=False)

                    colp1, colp2, colp3 = st.columns([5, 2, 1])
                    with colp1:
                        st.markdown(f"插件: `{_to_str(p_name)}`")
                        lvl, label = _effective_status_for_plugin(p_status, p_enabled)
                        badge = _build_status_badge(label, lvl, title=_to_str(p_status))
                        st.markdown(f"状态: {badge}", unsafe_allow_html=True)
                    with colp2:
                        plugin["enabled"] = st.toggle(
                            "启用插件",
                            value=p_enabled,
                            key=f"as_{i}_pl_{j}_enabled",
                        )
                        # 如用户切换开关，立刻更新徽章的生效状态
                        p_enabled = plugin["enabled"]
                    with colp3:
                        if st.button("🗑️", key=f"as_{i}_pl_{j}_remove", help=f"从 {name} 移除 {p_name}"):
                            dlg_key = f"{PREFIX_REMOVE}{assistant_id}_{p_name}"
                            st.session_state[dlg_key] = {
                                "open": True,
                                "result": None,
                                "payload": {"assistant_id": assistant_id, "assistant_name": name, "plugin_name": p_name},
                            }
                            st.rerun()

                    # 配置区
                    config_items = plugin.get("config")
                    if isinstance(config_items, list) and config_items:
                        st.markdown("用户配置:")
                        for config_item in config_items:
                            item_name = config_item.get("name")
                            if not item_name:
                                continue
                            item_type = config_item.get("type", "string")
                            is_required = config_item.get("required", False)
                            is_secret = config_item.get("secret", False)
                            description = config_item.get("description", f"设置 {item_name}")
                            default_value = config_item.get("default")
                            current_value = config_item.get("value")
                            label_txt = f"{item_name}{' (必填)' if is_required else ''}"
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
                        st.markdown("工具列表:")
                        for k, tool in enumerate(tools):
                            tool_name = tool.get("name") or f"tool_{k}"
                            tool_col1, tool_col2 = st.columns([3, 1])
                            with tool_col2:
                                is_enabled = st.toggle(
                                    "启用工具",
                                    value=_safe_bool(tool.get("enabled"), default=False),
                                    key=f"as_{i}_pl_{j}_tool_{k}_enabled",
                                )
                                tool["enabled"] = is_enabled
                            with tool_col1:
                                st.markdown(f"`{_to_str(tool_name)}`")
                                if is_enabled and tool.get("description"):
                                    st.caption(_to_str(tool.get("description")))


with tab_plugins:
    st.subheader("安装新插件 (占位符)")
    with bordered_container():
        st.text_input("从 Git Repository 安装", placeholder="https://github.com/user/my-agent-plugin.git")
        st.file_uploader("或上传插件 (.zip)")
        if st.button("安装插件", key="install_plugin_btn"):
            st.info("✨ 功能即将推出：通过 UI 安装插件的功能正在开发中。")
    st.markdown("---")
    st.subheader("所有可用的插件")
    st.caption("这里列出了插件目录中所有已成功加载的插件及其元数据。")
    available_plugins = get_available_plugins()
    if available_plugins is None:
        st.error("无法从后端获取插件列表。")
    elif not available_plugins:
        st.info("没有找到可用的插件。")
    else:
        for p_manifest in available_plugins:
            p_name = p_manifest.get("name", "未知插件")
            with st.expander(f"{p_name} (v{p_manifest.get('version', 'N/A')})"):
                st.markdown(f"> {p_manifest.get('description', '没有提供描述。')}")
                st.markdown("---")
                cols_info, cols_action = st.columns([3, 1])
                with cols_info:
                    st.markdown(f"规范版本: `{p_manifest.get('spec_version', 'N/A')}`")
                    mode = p_manifest.get("execution", {}).get("mode", "N/A")
                    st.markdown(f"执行模式: `{mode}`")
                with cols_action:
                    if st.button("🗑️ 删除", key=f"delete_btn_{p_name}", type="secondary"):
                        dlg_key = f"{PREFIX_DELETE}{p_name}"
                        st.session_state[dlg_key] = {
                            "open": True,
                            "result": None,
                            "payload": {"plugin_name": p_name},
                        }
                        st.rerun()
                dependencies = p_manifest.get("dependencies")
                if isinstance(dependencies, list) and dependencies:
                    st.markdown("依赖:")
                    st.code("\n".join(dependencies), language="text")

with tab_other_settings:
    st.subheader("LLM 提供商设置")
    llm_config = editable_settings.get("llm", {})
    llm_config["model"] = st.text_input("模型名称 (Model)", value=_to_str(llm_config.get("model")))
    llm_config["base_url"] = st.text_input("API Base URL", value=_to_str(llm_config.get("base_url")))
    llm_config["provider"] = st.text_input(
        "提供商 (Provider)",
        value=_to_str(llm_config.get("provider")),
        help="例如：'openai', 'anthropic' 等。",
    )
    llm_config["api_key"] = st.text_input(
        "API Key",
        value=_to_str(llm_config.get("api_key")),
        type="password",
        help="如果使用 OpenAI 等提供商，请在此处输入 API 密钥。",
    )
    st.markdown("---")
    st.subheader("通用设置")
    editable_settings["default_assistant"] = st.text_input(
        "默认助手名称 (Default Assistant)",
        value=_to_str(editable_settings.get("default_assistant")),
        help="当用户未指定时，默认使用的助手名称。",
    )

# --- Save Action ---
if save_clicked:
    with st.spinner("正在保存配置..."):
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
            st.toast("✅ 所有配置已成功保存并刷新！")
            st.rerun()
        else:
            st.error("❌ 保存失败，请检查上面的错误信息并重试。")

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
                "确认添加插件",
                f"确定要将插件 '{plugin_name}' 添加到助手 '{assistant_name}' 吗？",
                confirm_text="确认添加",
                cancel_text="取消",
            )
        elif state.get("result") in ("confirmed", "cancelled"):
            payload = (state.get("payload") or {}).copy()
            confirmed = state["result"] == "confirmed"
            st.session_state.pop(key, None)
            if confirmed:
                with st.spinner("正在添加插件..."):
                    ok = add_plugin_to_assistant_api(payload["assistant_id"], payload["plugin_name"])
                if ok:
                    st.toast(f"已向 {payload['assistant_name']} 添加插件 '{payload['plugin_name']}'", icon="✅")
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
                "确认移除插件",
                f"确定要从助手 '{assistant_name}' 中移除插件 '{plugin_name}' 吗？",
                confirm_text="确认移除",
                cancel_text="取消",
            )
        elif state.get("result") in ("confirmed", "cancelled"):
            payload = (state.get("payload") or {}).copy()
            confirmed = state["result"] == "confirmed"
            st.session_state.pop(key, None)
            if confirmed:
                with st.spinner("正在移除插件..."):
                    ok = remove_plugin_from_assistant_api(payload["assistant_id"], payload["plugin_name"])
                if ok:
                    st.toast(f"插件 '{payload['plugin_name']}' 已从 {payload['assistant_name']} 移除", icon="✅")
                    refresh_assistants_state()
                    st.rerun()

    if key.startswith(PREFIX_DELETE):
        state = st.session_state.get(key) or {}
        if state.get("open"):
            payload = state.get("payload", {})
            plugin_name = payload.get("plugin_name", "")
            render_confirm_dialog(
                key,
                "确认删除插件",
                f"确定要删除插件 '{plugin_name}' 吗？此操作可能影响已引用该插件的助手配置。",
                confirm_text="确认删除",
                cancel_text="取消",
            )
        elif state.get("result") in ("confirmed", "cancelled"):
            payload = (state.get("payload") or {}).copy()
            confirmed = state["result"] == "confirmed"
            st.session_state.pop(key, None)
            if confirmed:
                with st.spinner("正在删除插件..."):
                    ok = remove_plugin(payload["plugin_name"])
                if ok:
                    st.toast(f"插件 '{payload['plugin_name']}' 已删除", icon="✅")
                    refresh_assistants_state()
                    st.rerun()
