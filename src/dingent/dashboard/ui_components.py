import inspect

import streamlit as st
import streamlit_antd_components as sac  # uses sac.tags + sac.Tag
from streamlit_modal import Modal  # confirmation dialogs


def inject_base_css():
    """Minimal spacing tweaks."""
    st.markdown(
        """
<style>
.block-container { padding-top: 0.75rem; }
.stTabs [role="tab"] { padding: 0.35rem 0.8rem; font-size: 0.95rem; }
.stAlert { margin: 0.25rem 0 !important; }
div[data-testid="stButton"] > button { min-height: 2rem; }
</style>
        """,
        unsafe_allow_html=True,
    )


def bordered_container():
    """Bordered container compatible with different Streamlit versions."""
    try:
        sig = inspect.signature(st.container)
        if "border" in sig.parameters:
            return st.container(border=True)
    except Exception:
        pass
    return st.container()


def status_tag(label: str, level: str, id: str):
    """
    Render a status tag using streamlit-antd-components new API:
      sac.tags([sac.Tag(...)] , align='left')

    level: ok | warn | error | disabled | unknown
    """
    level = (level or "unknown").lower()
    label = label or "Unknown"

    # Color can be a string (hex) or preset; use hex to be explicit.
    color_map = {
        "ok": "#137333",  # green
        "warn": "#b25e09",  # orange
        "error": "#b3261e",  # red
        "disabled": "#5f6368",  # gray
        "unknown": "#1a73e8",  # blue
    }
    sac.tags(
        [
            sac.Tag(
                label=label,
                color=color_map.get(level, "#1a73e8"),
                bordered=True,
                closable=False,
                radius="xl",
                size="sm",
            )
        ],
        align="left",
        key=f"status_tag_{label}_{level}_{id}",
    )


def render_confirm_dialog(
    state_key: str,
    title: str,
    message: str,
    confirm_text: str = "Confirm",
    cancel_text: str = "Cancel",
):
    """
    Confirmation dialog using streamlit-modal.
    点击按钮时只设置状态，不调用 st.rerun；
    按钮点击结束后，Streamlit 会自动重跑一次，下一轮即会根据状态关闭弹窗或执行后续逻辑。
    """
    modal = Modal(title, key=f"{state_key}_modal", max_width=600)
    modal.open()
    with modal.container():
        st.write(message)
        c1, c2 = st.columns(2)
        with c1:
            if st.button(confirm_text, type="primary", key=f"{state_key}_confirm_modal"):
                st.session_state[state_key]["result"] = "confirmed"
                st.session_state[state_key]["open"] = False
        with c2:
            if st.button(cancel_text, key=f"{state_key}_cancel_modal"):
                st.session_state[state_key]["result"] = "cancelled"
                st.session_state[state_key]["open"] = False
