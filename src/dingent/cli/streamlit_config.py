"""
Streamlit configuration editor for Dingent projects.

This module provides a web-based GUI for editing Dingent configuration files
using Streamlit. It allows users to modify assistant settings, plugin configurations,
and LLM settings through an intuitive interface.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st
import tomlkit
from loguru import logger

# Add the source directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from dingent.utils import find_project_root
except ImportError:
    # Fallback for development environment
    def find_project_root(marker: str = "dingent.toml"):
        """Find project root by looking for marker file."""
        current_dir = Path.cwd().resolve()
        while current_dir != current_dir.parent:
            if (current_dir / marker).exists():
                return current_dir
            current_dir = current_dir.parent
        if (current_dir / marker).exists():
            return current_dir
        return None


class ConfigManager:
    """Manages reading and writing of Dingent configuration files."""
    
    def __init__(self):
        self.project_root = find_project_root()
        if not self.project_root:
            st.error("❌ Not in a Dingent project directory. Please run this from a Dingent project.")
            st.stop()
        
        self.config_path = self.project_root / "backend" / "config.toml"
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from TOML file."""
        if not self.config_path.exists():
            # Return default configuration structure
            return {
                "llm": {"model": "gpt-4.1"},
                "assistants": []
            }
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return tomlkit.parse(content).unwrap()
        except Exception as e:
            st.error(f"Error loading config: {e}")
            return {"llm": {"model": "gpt-4.1"}, "assistants": []}
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to TOML file."""
        try:
            # Ensure backend directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to TOML document
            doc = tomlkit.document()
            
            # Add LLM configuration
            if "llm" in config:
                llm_table = tomlkit.table()
                for key, value in config["llm"].items():
                    llm_table[key] = value
                doc["llm"] = llm_table
            
            # Add assistants configuration
            if "assistants" in config:
                for assistant in config["assistants"]:
                    assistant_table = tomlkit.table()
                    for key, value in assistant.items():
                        if key == "tools":
                            # Tools need special handling as array of inline tables
                            tools_array = tomlkit.array()
                            for tool in value:
                                tool_table = tomlkit.inline_table()
                                for tool_key, tool_value in tool.items():
                                    if isinstance(tool_value, dict):
                                        # Nested dicts (like database config) need special handling
                                        nested_str = ".".join([f"{k}=\"{v}\"" for k, v in tool_value.items()])
                                        # For now, we'll serialize nested dicts as strings
                                        # This is a simplification that works for the common case
                                        for nested_key, nested_value in tool_value.items():
                                            tool_table[f"{tool_key}.{nested_key}"] = nested_value
                                    else:
                                        tool_table[tool_key] = tool_value
                                tools_array.append(tool_table)
                            assistant_table["tools"] = tools_array
                        else:
                            assistant_table[key] = value
                    
                    doc.append("assistants", assistant_table)
            
            # Write to file
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(tomlkit.dumps(doc))
            
            return True
        except Exception as e:
            st.error(f"Error saving config: {e}")
            return False


def render_llm_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Render LLM configuration section."""
    st.subheader("🤖 LLM Configuration")
    
    llm_config = config.get("llm", {})
    
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            model = st.text_input(
                "Model Name",
                value=llm_config.get("model", "gpt-4.1"),
                help="The LLM model to use (e.g., gpt-4.1, gpt-3.5-turbo)"
            )
        
        with col2:
            # Allow for additional LLM settings
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=2.0,
                value=float(llm_config.get("temperature", 0.7)),
                step=0.1,
                help="Controls randomness in responses"
            )
    
    # Advanced settings in expander
    with st.expander("Advanced LLM Settings"):
        max_tokens = st.number_input(
            "Max Tokens",
            min_value=1,
            max_value=32000,
            value=int(llm_config.get("max_tokens", 4000)),
            help="Maximum number of tokens in response"
        )
        
        api_base = st.text_input(
            "API Base URL",
            value=llm_config.get("api_base", ""),
            help="Custom API base URL (optional)"
        )
    
    updated_llm = {"model": model, "temperature": temperature}
    if max_tokens != 4000:
        updated_llm["max_tokens"] = max_tokens
    if api_base:
        updated_llm["api_base"] = api_base
    
    return updated_llm


def render_tool_config(tool: Dict[str, Any], tool_index: int) -> Dict[str, Any]:
    """Render configuration for a single tool."""
    with st.container():
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            plugin_name = st.text_input(
                "Plugin Name",
                value=tool.get("plugin_name", ""),
                key=f"tool_plugin_{tool_index}"
            )
        
        with col2:
            name = st.text_input(
                "Tool Name",
                value=tool.get("name", ""),
                key=f"tool_name_{tool_index}"
            )
        
        with col3:
            if st.button("🗑️", key=f"delete_tool_{tool_index}", help="Delete this tool"):
                return None  # Signal for deletion
        
        # Tool-specific configuration
        updated_tool = {"plugin_name": plugin_name, "name": name}
        
        # Add other tool properties
        for key, value in tool.items():
            if key not in ["plugin_name", "name"]:
                if isinstance(value, dict):
                    # Handle nested configurations (like database config)
                    with st.expander(f"{key.title()} Configuration"):
                        nested_config = {}
                        for nested_key, nested_value in value.items():
                            nested_config[nested_key] = st.text_input(
                                nested_key.replace("_", " ").title(),
                                value=str(nested_value),
                                key=f"tool_{tool_index}_{key}_{nested_key}"
                            )
                        updated_tool[key] = nested_config
                else:
                    # Simple value
                    if key == "llm.model":
                        # Handle LLM model specifically
                        updated_tool["llm"] = {"model": st.text_input(
                            "LLM Model",
                            value=str(value),
                            key=f"tool_{tool_index}_llm_model"
                        )}
                    else:
                        updated_tool[key] = st.text_input(
                            key.replace("_", " ").title(),
                            value=str(value),
                            key=f"tool_{tool_index}_{key}"
                        )
        
        return updated_tool


def render_assistant_config(assistant: Dict[str, Any], assistant_index: int) -> Dict[str, Any]:
    """Render configuration for a single assistant."""
    with st.container():
        st.markdown("---")
        
        # Assistant header with delete button
        col1, col2 = st.columns([4, 1])
        with col1:
            st.subheader(f"👤 Assistant: {assistant.get('name', 'Unnamed')}")
        with col2:
            if st.button("🗑️ Delete Assistant", key=f"delete_assistant_{assistant_index}"):
                return None  # Signal for deletion
        
        # Basic assistant settings
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input(
                "Assistant Name",
                value=assistant.get("name", ""),
                key=f"assistant_name_{assistant_index}"
            )
        
        with col2:
            enabled = st.checkbox(
                "Enabled",
                value=assistant.get("enabled", True),
                key=f"assistant_enabled_{assistant_index}"
            )
        
        description = st.text_area(
            "Description",
            value=assistant.get("description", ""),
            height=100,
            key=f"assistant_description_{assistant_index}",
            help="This description serves as the system prompt for the LLM"
        )
        
        # Tools configuration
        st.write("🔧 **Tools Configuration**")
        
        tools = assistant.get("tools", [])
        updated_tools = []
        
        for tool_index, tool in enumerate(tools):
            st.write(f"**Tool {tool_index + 1}**")
            updated_tool = render_tool_config(tool, f"{assistant_index}_{tool_index}")
            if updated_tool is not None:  # Not deleted
                updated_tools.append(updated_tool)
        
        # Add new tool button
        if st.button(f"➕ Add New Tool", key=f"add_tool_{assistant_index}"):
            updated_tools.append({
                "plugin_name": "",
                "name": "",
            })
        
        return {
            "name": name,
            "description": description,
            "enabled": enabled,
            "tools": updated_tools
        }


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Dingent Configuration Editor",
        page_icon="⚙️",
        layout="wide"
    )
    
    st.title("⚙️ Dingent Configuration Editor")
    st.markdown("Edit your Dingent project configuration through this web interface.")
    
    # Initialize config manager
    config_manager = ConfigManager()
    
    # Load current configuration
    if "config" not in st.session_state:
        st.session_state.config = config_manager.load_config()
    
    # Create tabs for different configuration sections
    tab1, tab2, tab3 = st.tabs(["🤖 LLM Settings", "👥 Assistants", "💾 Save & Load"])
    
    with tab1:
        st.session_state.config["llm"] = render_llm_config(st.session_state.config)
    
    with tab2:
        st.markdown("Manage your AI assistants and their tools.")
        
        assistants = st.session_state.config.get("assistants", [])
        updated_assistants = []
        
        for i, assistant in enumerate(assistants):
            updated_assistant = render_assistant_config(assistant, i)
            if updated_assistant is not None:  # Not deleted
                updated_assistants.append(updated_assistant)
        
        # Add new assistant button
        if st.button("➕ Add New Assistant"):
            updated_assistants.append({
                "name": f"assistant_{len(updated_assistants) + 1}",
                "description": "New assistant description",
                "enabled": True,
                "tools": []
            })
        
        st.session_state.config["assistants"] = updated_assistants
    
    with tab3:
        st.subheader("💾 Save Configuration")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Save Configuration", type="primary"):
                if config_manager.save_config(st.session_state.config):
                    st.success("✅ Configuration saved successfully!")
                    st.balloons()
        
        with col2:
            if st.button("🔄 Reload from File"):
                st.session_state.config = config_manager.load_config()
                st.success("✅ Configuration reloaded from file!")
                st.rerun()
        
        with col3:
            if st.button("⚠️ Reset to Default"):
                st.session_state.config = {"llm": {"model": "gpt-4.1"}, "assistants": []}
                st.warning("⚠️ Configuration reset to default!")
                st.rerun()
        
        # Show current configuration as JSON
        with st.expander("📄 View Raw Configuration"):
            st.json(st.session_state.config)
        
        # Configuration file info
        st.info(f"📁 Configuration file: `{config_manager.config_path}`")


if __name__ == "__main__":
    main()