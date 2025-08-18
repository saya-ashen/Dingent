import inspect

import streamlit as st


def inject_base_css():
    """Inject base styles to unify control sizes and spacing, improving usability."""
    st.markdown(
        """
<style>
:root {
  --btn-padding-y: 0.35rem;
  --btn-padding-x: 0.7rem;
  --btn-font-size: 0.92rem;
  --btn-radius: 8px;
  --btn-line-height: 1.1rem;

  /* Status badge colors (light theme) */
  --status-ok-bg: #e6f4ea;
  --status-ok-fg: #137333;
  --status-warn-bg: #fff4e5;
  --status-warn-fg: #b25e09;
  --status-error-bg: #fdecea;
  --status-error-fg: #b3261e;
  --status-disabled-bg: #f1f3f4;
  --status-disabled-fg: #5f6368;
  --status-unknown-bg: #e8f0fe;
  --status-unknown-fg: #1a73e8;
}

@media (prefers-color-scheme: dark) {
  :root {
    /* Status badge colors (dark theme) */
    --status-ok-bg: rgba(52, 168, 83, 0.15);
    --status-ok-fg: #7bd88f;
    --status-warn-bg: rgba(251, 140, 0, 0.18);
    --status-warn-fg: #ffb74d;
    --status-error-bg: rgba(211, 47, 47, 0.18);
    --status-error-fg: #ef9a9a;
    --status-disabled-bg: rgba(189, 189, 189, 0.16);
    --status-disabled-fg: #bdbdbd;
    --status-unknown-bg: rgba(25, 118, 210, 0.18);
    --status-unknown-fg: #90caf9;
  }
}

.block-container { padding-top: 0.75rem; }
.stTabs [role="tab"] { padding: 0.35rem 0.8rem; font-size: 0.95rem; }
.st-emotion-cache-ue6h4q { gap: 0.5rem; } /* tabs gap in some themes */
.stAlert { margin: 0.25rem 0 !important; }

div[data-testid="stButton"] > button {
  padding: var(--btn-padding-y) var(--btn-padding-x);
  font-size: var(--btn-font-size);
  line-height: var(--btn-line-height);
  border-radius: var(--btn-radius);
  min-height: 2rem;
}

div[data-testid="stButton"] > button:hover {
  filter: brightness(0.98);
}

div[data-testid="stButton"] > button:active {
  transform: translateY(0.5px);
}

.st-expanderHeader { font-size: 0.95rem; }
.stTextInput > div > div > input,
.stTextArea textarea,
.stNumberInput input {
  font-size: 0.95rem;
}

/* Enlarge help icon and increase clickable area */
[data-testid="stTooltipIcon"] {
  margin-left: 6px;
  padding: 2px;
  border-radius: 6px;
  opacity: 0.95;
}
[data-testid="stTooltipIcon"] svg {
  width: 1rem;
  height: 1rem;
}

/* Status badge styles */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  border: 1px solid transparent;
  font-size: 0.9rem;
  font-weight: 600;
  line-height: 1.2rem;
  vertical-align: middle;
  user-select: none;
  white-space: nowrap;
}
.status-badge .dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: currentColor;
  flex: 0 0 auto;
}
.status-ok {
  color: var(--status-ok-fg);
  background: var(--status-ok-bg);
  border-color: color-mix(in srgb, var(--status-ok-fg) 25%, transparent);
}
.status-warn {
  color: var(--status-warn-fg);
  background: var(--status-warn-bg);
  border-color: color-mix(in srgb, var(--status-warn-fg) 25%, transparent);
}
.status-error {
  color: var(--status-error-fg);
  background: var(--status-error-bg);
  border-color: color-mix(in srgb, var(--status-error-fg) 25%, transparent);
}
.status-disabled {
  color: var(--status-disabled-fg);
  background: var(--status-disabled-bg);
  border-color: color-mix(in srgb, var(--status-disabled-fg) 25%, transparent);
}
.status-unknown {
  color: var(--status-unknown-fg);
  background: var(--status-unknown-bg);
  border-color: color-mix(in srgb, var(--status-unknown-fg) 25%, transparent);
}
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


def _has_dialog() -> bool:
    """Detect whether the current Streamlit version supports st.dialog."""
    return hasattr(st, "dialog")


def render_confirm_dialog(state_key: str, title: str, message: str, confirm_text: str = "Confirm", cancel_text: str = "Cancel"):
    """
    Render a confirmation dialog.
    - Use st.dialog (if available) to display modally;
    - Otherwise fall back to an inline warning block with Confirm/Cancel buttons.
    Clicking the buttons sets st.session_state[state_key]["result"] to "confirmed"/"cancelled" and closes the dialog.
    """
    if _has_dialog():

        @st.dialog(title)
        def _dlg():
            st.write(message)
            c1, c2 = st.columns(2)
            with c1:
                if st.button(confirm_text, type="primary", key=f"{state_key}_confirm"):
                    st.session_state[state_key]["result"] = "confirmed"
                    st.session_state[state_key]["open"] = False
                    st.rerun()
            with c2:
                if st.button(cancel_text, key=f"{state_key}_cancel"):
                    st.session_state[state_key]["result"] = "cancelled"
                    st.session_state[state_key]["open"] = False
                    st.rerun()

        _dlg()
    else:
        st.warning(message)
        c1, c2 = st.columns(2)
        with c1:
            if st.button(confirm_text, type="primary", key=f"{state_key}_confirm_fallback"):
                st.session_state[state_key]["result"] = "confirmed"
                st.session_state[state_key]["open"] = False
                st.rerun()
        with c2:
            if st.button(cancel_text, key=f"{state_key}_cancel_fallback"):
                st.session_state[state_key]["result"] = "cancelled"
                st.session_state[state_key]["open"] = False
                st.rerun()
