---
sidebar_position: 2
---

# Configuration

We use [**Pydantic-Settings**](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) to manage configuration in Dingent. This allows you to define your configuration in a structured way, with support for environment variables, default values, and type validation. However, we recommend using a TOML file to manage your configuration, which is the default approach in our templates.
For secret keys like `OPENAI_API_KEY`, you can set them as environment variables or use a `.env` file.

## Plugin Configuration

- **Concept: Tool / Plugin**

    In the Dingent framework, a **Tool** or **Plugin** is the smallest functional unit the system can execute. You can think of it as a specific skill available to an Agent. For example:

  * A tool that can **check the weather**.
  * A tool that can **send an email**.
  * A tool that can **execute a database query**.
  * A tool that can **say hello**, like in our previous examples.

Each tool is created by a developer and encapsulates the logic for interacting with the external world or performing a specific computation. As a user, your main task is to enable and configure these tools within your assistant's configuration to meet your specific needs.

- **How to Configure Tools?**

    You do not need a separate configuration file for tools. A tool's configuration is defined directly inside the **Assistant** that will use it.

    The workflow for managing and using plugins is as follows:

    -  **Obtain the Plugin**: Written by a developer or downloaded from the community, and placed in the project's `assistants/plugins` directory.
    -  **View Available Plugins**: You can use the command-line tool to see all currently loaded and available plugins.
        ```bash
        dingent assistants plugin list
        ```
    -  **Configure the Plugin in an Assistant**: In the assistant's configuration file, fill in the specific settings for the plugin you want to use. You can see a detailed example in the "Assistant" documentation below.

-----

## Assistant Configuration

- **Concept: Assistant**

    An **Assistant is a collection of tools oriented toward a specific domain task**.

    If a "tool" is a screwdriver or a wrench, then an "assistant" is a complete **toolbox** prepared for a specific job, like "repairing a computer" or "assembling furniture." It contains not only the tools needed to complete the task but also **high-level instructions** on how to perform it.

    For example, you could create:

  * **A General Chat Assistant**: Configured with tools for "greeting," "weather checking," "web search," etc.
  * **A Data Analysis Assistant**: Directly integrates a series of professional tools in its configuration, such as "database connection" and "SQL execution."
  * **A Customer Service Assistant**: Includes configurations for tools like "order lookup," "knowledge base retrieval," and "ticket creation."

    As a user, you can create multiple agents with different capabilities and personalities by defining different assistants.

- **How to Configure an Assistant?**

    You can define one or more assistants in a single `TOML` configuration file. Each assistant's configuration primarily includes its basic information (like name), behavioral instructions, and the **tools it is authorized to use, along with their detailed configurations**.

    We recommend using the `.toml` format to manage your assistant configurations because it clearly represents complex nested structures.

    **Configuration File Example**

  * **File Location**: `assistants/config.toml`

<!-- end list -->

```toml
# "[[assistants]]" defines a specific assistant instance.
# You can define multiple [[assistants]] blocks in the same file.

[[assistants]]
name = "sakila"
host = "localhost"
port = "8888"
description = """
This assistant can only answer questions about the operations of a DVD rental business stored in the database. The query should be about analyzing business performance, customer behavior, or film inventory.

Use this tool for questions about:
- Sales & Revenue: Find sales figures, total revenue for stores or films, and details about specific payments.
- Customer Analysis: Inquire about customer rental habits, find top customers, or analyze customer demographic data like their location.
- Film & Inventory: Find films by title, genre (category), or actor. Check inventory levels for a specific film at a particular store.
- Store & Staff Operations: Explore information about individual stores, their staff, and the rental transactions they process.
"""

# The "tools" list directly defines and configures the tools available to this assistant.
tools = [
  {
    type = "text2sql",
    name = "sakila_text2sql",
    description = "A tool to translate natural language questions into SQL queries for the Sakila database.",

    # --- Configuration specific to the text2sql type ---
    llm = { model="gpt-4.1", provider="openai" },
    database = {
      name = "sakila",
      uri = "sqlite:///./data/sakila.db",
      schemas_file = "schemas/sakila.py"
    }
  }
]

# [[assistants]]
# name = "another_assistant"
# ... configuration for more assistants ...
```

- **Configuration Fields Explained**
      - `name` (Required): The unique name you assign to this assistant.
      * `host` (Optional): The IP address for exposing this assistant's service.
      * `port` (Optional): The port for exposing this assistant's service.
      * `description` (Required): A detailed description of this assistant's function. This content also serves as the **core instruction (System Prompt)** for the large language model. The model will strictly follow these instructions, which determines its personality, behavioral guidelines, and task objectives. You can use `"""` for multi-line text.
      * `tools` (Required): A list that **directly defines and configures** all the tools this assistant is authorized to use.
          * This is a list of configuration objects, not just a list of IDs.
          * The fields within each tool object (e.g., `type`, `name`, `llm`, `database`) are determined by its plugin type.
          * You will need to consult the specific plugin's `README.md` or related documentation to understand its configurable parameters and how to fill them out.
