# Dingent Configuration GUI

This document describes how to use the new Streamlit-based configuration GUI for Dingent projects.

## Overview

The Configuration GUI provides a web-based interface for editing Dingent project configurations. Instead of manually editing TOML files, users can now use an intuitive graphical interface to manage their assistants, plugins, and LLM settings.

## Features

### 🤖 LLM Configuration
- **Model Selection**: Choose and configure your LLM model (GPT-4, GPT-3.5, etc.)
- **Parameter Tuning**: Adjust temperature, max tokens, and other model parameters
- **Custom API Settings**: Configure custom API base URLs for alternative providers

### 👥 Assistant Management
- **Add/Edit/Delete Assistants**: Full CRUD operations for AI assistants
- **Tool Configuration**: Manage tools and plugins for each assistant
- **Nested Settings**: Configure complex tool settings like database connections
- **Enable/Disable**: Toggle assistants on/off without deleting them

### 💾 Configuration Management  
- **Save Changes**: Write configuration back to TOML files
- **Live Preview**: View raw configuration as JSON
- **Reload/Reset**: Reload from file or reset to defaults
- **Validation**: Basic validation of configuration structure

## Usage

### Starting the GUI

From your Dingent project directory, run:

```bash
dingent config gui
```

By default, this starts the interface on port 8501. To use a different port:

```bash
dingent config gui --port 8502
```

The command will open your default browser to `http://localhost:8501` where you can access the configuration interface.

### Interface Layout

The GUI is organized into three main tabs:

1. **🤖 LLM Settings**: Configure your language model settings
2. **👥 Assistants**: Manage your AI assistants and their tools  
3. **💾 Save & Load**: Save changes and view raw configuration

### Editing Assistants

1. Navigate to the "👥 Assistants" tab
2. Edit existing assistants or click "➕ Add New Assistant"
3. Configure basic settings:
   - **Name**: Unique identifier for the assistant
   - **Description**: System prompt and behavioral instructions
   - **Enabled**: Whether the assistant is active
4. Configure tools:
   - **Plugin Name**: The plugin providing the tool
   - **Tool Name**: Specific tool identifier
   - **Nested Settings**: Database connections, LLM overrides, etc.

### Saving Changes

1. Go to the "💾 Save & Load" tab
2. Click "💾 Save Configuration" to write changes to `backend/config.toml`
3. Use "🔄 Reload from File" to discard unsaved changes
4. Use "⚠️ Reset to Default" to start with a clean configuration

## Configuration File Structure

The GUI reads and writes standard Dingent configuration files in TOML format:

```toml
llm.model = "gpt-4.1"

[[assistants]]
name = "text2sql_assistant"
description = "Assistant for text2sql queries"
enabled = true
tools = [
  {
    plugin_name = "text2sql",
    name = "s-text2sql",
    llm.model = "gpt-4.1",
    database.name = "sakila",
    database.uri = "sqlite:///./data/sakila.db"
  }
]
```

## Requirements

- Streamlit >= 1.48.1 (included in Dingent dependencies)
- Python >= 3.12
- Must be run from within a Dingent project directory

## Troubleshooting

### "Not in a Dingent project directory"
Ensure you're running the command from a directory containing a `dingent.toml` file.

### "Streamlit is not installed"
Streamlit should be installed automatically with Dingent. If not, install it manually:
```bash
pip install streamlit
```

### Port already in use
Use the `--port` option to specify a different port:
```bash
dingent config gui --port 8502
```

### Configuration not saving
Check that you have write permissions to the `backend/config.toml` file and that the `backend/` directory exists.

## Implementation Details

The configuration GUI is implemented in `src/dingent/cli/streamlit_config.py` and integrated into the CLI via `src/dingent/cli/cli.py`. It uses:

- **Streamlit**: For the web interface
- **tomlkit**: For preserving TOML formatting and comments
- **Pydantic**: For configuration validation (future enhancement)

The interface is designed to be intuitive for both technical and non-technical users while maintaining the full power and flexibility of the underlying configuration system.