---
sidebar_position: 3
---

# Project Structure

When you first run the `uvx dingent dev` command in an empty directory, Dingent initializes a standard project structure for you. Understanding the purpose of each file and directory is the first step to effective development.

A typical Dingent project contains the following parts:

```plaintext
my-awesome-agent/
├── 📄 dingent.toml      # The main project configuration file
├── 📁 config/            # Configurations managed by the Admin Dashboard
│   ├── 📁 assistants/
│   ├── 📁 plugins/
│   └── 📁 workflows/
└── 📁 plugins/       # Stores plugins from the Market and custom plugins
```

Let's break down the role of each part in detail.

### The Root Directory

This is the top-level directory for your project, e.g., `my-awesome-agent/`. All `dingent` CLI commands should be run from this directory.

### `dingent.toml`

This is the most important file in your project, serving two core functions:

1.  **Project Identifier**: Its presence tells the Dingent CLI that the current directory is a project root.
2.  **Core Configuration**: It contains the project's core static configuration, such as the backend server port, default LLM settings, and other global parameters.

While you can edit this file manually, many settings (especially LLM configuration) can also be managed via the **Admin Dashboard**.

**Example `dingent.toml` Content:**

```toml
backend_port = 8000
frontend_port = 3000
workflows = []
current_workflow = "tech-trends-workflow"

[llm]
model = "openai/gpt-4.1"
base_url = "https://api.openai.com/v1"
api_key = "keyring:llm.api_key"

```

### The `config/` Directory

This directory stores all the dynamic configurations created and managed through the **Admin Dashboard**. **You should generally not edit the files in this directory manually**, as your changes may be overwritten by actions taken in the UI.

  * **`config/assistants/`**: Stores the configuration files for each Assistant you create (e.g., their names, instructions).
  * **`config/plugins/`**: Stores configuration information for the plugins (e.g., Api keys).
  * **`config/workflows/`**: Stores the structure and configuration for each Workflow you design.

Note: All the secret values (like API keys) are securely stored using the [Keyring](https://pypi.org/project/keyring/) library, ensuring they are not exposed in plain text.
But if you don't have a system keyring set up, they will be stored as encrypted values in the .dingent directory.

### The `plugins/` Directory

This directory serves as the central repository for all tools and skills your agent can use. Its primary purpose is to store plugins downloaded from the **Market**.

When you install a plugin from the Admin Dashboard, its code is placed here. Dingent automatically discovers these plugins, making them available to be assigned to your Assistants.

For developers who wish to create their own tools, this directory can also be used to house custom plugins. Simply place your plugin's code here, and the framework will load it alongside the ones from the Market.

## Next Steps

Now that you understand the basic structure of a Dingent project, it's time to start configuring your agent.
In the next section, we'll guide you through using the Admin Dashboard to handle all the core setup.

➡️ **Next: [Admin Dashboard Guide](../admin-dashboard-guide/overview.md)**
