---
sidebar_position: 1
---
# Plugins Development

## Quick Start

The process of developing a new plugin is very straightforward. First, you will need a Dingent project.

### Step 1: Initialize the Project

If you don't already have a project, please refer to the [Installation](../getting-started/installation.md) section to create one.

### Step 2: Create the Plugin Directory

All plugins are located in the `assistants/plugins/` directory within the project's root. Please create a dedicated directory for your new plugin. The directory name should clearly describe the plugin's functionality, such as `greeter` or `weather_checker`.

```bash
mkdir -p assistants/plugins/greeter
```

## Plugin Structure Explained

A standard Dingent plugin contains the following file structure. Each file serves a specific purpose.

```
assistants/plugins/greeter/
├── __init__.py      # Marks the directory as a Python package
├── plugin.toml      # Core metadata and configuration for the plugin
├── settings.py      # Defines the plugin's configurable options
├── tool.py          # The plugin's main logic implementation
└── README.md        # Documentation for the plugin
```

Next, we will explain the role of each file in detail.

### `plugin.toml` (Core Configuration File)

This is the plugin's entry point definition file. It tells the Dingent system how to load and use your plugin.

**Example:**

```toml
[plugin]
# The plugin's name, which should be unique
name = "greeter"

# The plugin's version, following Semantic Versioning
version = "1.0.0"

# A reference path to the plugin's main logic class
# The format is "filename:ClassName", referring to the Greeter class in tool.py
tool_class = "tool:Greeter"

# The plugin specification version
spec_version = 1.0

# The required Python dependencies for the plugin to run
# The system will automatically install these dependencies via the `dingent assistants plugin sync` command
dependencies = [
    "pandas>=2.2.3",
]
```

**Field Descriptions:**

  * `name`: The unique identifier for the plugin.
  * `version`: The current version of the plugin.
  * `tool_class`: A pointer to the plugin's main class, which serves as the logic entry point.
  * `spec_version`: The version of the plugin specification you are adhering to.
  * `dependencies`: A list of all required third-party Python libraries.

### `tool.py` (Main Logic File)

This file contains the core functional code of the plugin. The class you specify in `plugin.toml` via `tool_class` is defined here.

**Key Requirement:**

  * Your main tool class (e.g., `Greeter`) **must** inherit from `dingent.engine.plugins.BaseTool`.

**Example `tool.py`:**

```python
# tool.py
from typing import Annotated
from pydantic import Field

# Import core framework components
from dingent.engine.plugins import BaseTool
from dingent.engine.resource import ToolOutput, TablePayload

# Import the Settings class from the sibling settings.py file
from .settings import Settings

class Greeter(BaseTool):
    """A simple greeting tool to demonstrate basic plugin structure."""

    def __init__(
        self,
        config: Settings,
        **kwargs,
    ):
        # Initialize the parent class, passing in the configuration
        super().__init__(config, **kwargs)
        # self.resource_manager is automatically injected by the system and can be used to register resources.

    async def tool_run(
        self,
        target: Annotated[str, Field(description="The name of the person to greet.")],
    ) -> dict:
        """
        The core method that runs the tool.
        The large language model will decide how to call this method based on its parameter signature and description.
        """
        # 1. Prepare the tool output content to be stored
        tool_output_payload = TablePayload(
            columns=["greeter", "target"],
            rows=[{"greeter": self.name, "target": target}]
        )

        # 2. Use the resource manager to register the output and get an ID
        # This allows complex or large run results (like tables or files) to be stored for later display or analysis.
        tool_output_ids = [
            self.resource_manager.register(
                ToolOutput(type="greeter_output", payload=tool_output_payload)
            )
        ]

        # 3. Build and return a dictionary with three key elements
        return {
            "context": f"{self.name} just said hello to {target}.",
            "tool_output_ids": tool_output_ids,
            "source": "greeter"
        }
```

#### Code Explanation

  * **`__init__(...)`**: The constructor. When the framework initializes the plugin, it passes in the user-configured `Settings` object. System dependencies like `resource_manager` are automatically injected by the framework and do not need to be instantiated manually.

  * **`async def tool_run(...)`**: This is the execution entry point for the tool.

      * **Method Parameters (`target: Annotated[...]`)**: These parameters are directly exposed to the Large Language Model (LLM). The model uses the parameter's type hints (`str`) and the `description` within `Field` to understand how to call this tool. **A clear and accurate `description` is crucial for the model to call the tool correctly.**

  * **`resource_manager`**: This is a system-injected dependency. Its core function is to provide a `register` method that allows you to store the tool's execution results (e.g., a table, an image, a code snippet) as a standardized `ToolOutput` object. Registration returns a unique resource ID.

  * **`tool_output_ids`**: This is a list of resource IDs. When your tool generates data that needs to be stored and displayed independently (like a data analysis table), you should register it and place the resulting ID in this list. This enables the UI or other system components to fetch and display these structured results using their IDs.

  * **`return` Dictionary**: The `tool_run` method returns a structured dictionary containing three key fields:

      * `"context"`: The content of this field is the **actual text** provided to the LLM to generate its final reply. The model will use the `context` to understand what the tool accomplished and formulate its response to the user. It should be a concise, clear statement of fact.
      * `"tool_output_ids"`: Returns the list of resource IDs you just registered.
      * `"source"`: Declares the origin of this result, which is typically the plugin's name.

### `settings.py` (Configuration File)

This file is used to define the plugin's configurable parameters, such as API keys, default host addresses, or behavioral switches. This allows users to easily adjust the plugin's behavior without modifying the core code.

**Key Requirement:**

  * Your configuration class  **must** be named `Settings` and inherit from `ToolBaseSettings`.

**Example `settings.py`:**

```python
# settings.py
from dingent.engine.plugins import ToolBaseSettings

class Settings(ToolBaseSettings):
    """
    Configuration settings for the Greeter plugin.
    Fields defined here will become required parameters during the plugin's initialization.
    """
    greeterName: str
```

## Dependency Management

While developing your plugin, you might use third-party libraries (e.g., `requests`, `pandas`). You should add these libraries to the `dependencies` list in your `plugin.toml` file.

After completing development or updating dependencies, run the following command in the **project's root directory**:

```bash
dingent assistants plugin sync
```

This command will automatically scan all plugins in the `assistants/plugins/` directory, read their `plugin.toml` files, and install all declared dependencies into your current environment. This ensures a consistent runtime environment for the plugin.
