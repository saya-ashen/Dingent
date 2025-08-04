---
sidebar_position: 2
---

# Configuration
We use [**Pydantic-Settings**](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) to manage configuration in Dingent. This allows you to define your configuration in a structured way, with support for environment variables, default values, and type validation. But we recommend to use the toml file to manage your configuration, which is used in our templates by default.
For secret keys like `OPENAI_API_KEY`, you can set them as environment variables or use a `.env` file.

## MCP Servers Configuration
The MCP servers configuration is defined in the `config.toml` file in mcp directory. This file allows you to specify multiple MCP servers, each with its own configuration. The default configuration in basic template is as follows:

```toml
[[databases]]
name = "sakila"
uri = "sqlite:///./data/sakila.db"
schemas_file = "schemas/sakila.py"
[[mcp_servers]]
name = "sakila"
llm.provider = "openai"
llm.model = "gpt-4.1"
database = "sakila"
enabled_tools = ["text2sql"]
host = "127.0.0.1"
port = "8888"
description = "This assistant can only answer questions about the operations of a DVD rental business stored in the database. The query should be about analyzing business performance, customer behavior, or film inventory.\n\nUse this tool for questions about:\n- Sales & Revenue: Find sales figures, total revenue for stores or films, and details about specific payments.\n- Customer Analysis: Inquire about customer rental habits, find top customers, or analyze customer demographic data like their location.\n- Film & Inventory: Find films by title, genre (category), or actor. Check inventory levels for a specific film at a particular store.\n- Store & Staff Operations: Explore information about individual stores, their staff, and the rental transactions they process.\n\n"
```

### Configuration Explained

This configuration file sets up an AI assistant that can answer questions about a database. We use the **"Sakila"** database in this guide, which is a **sample dataset included in our template** to show you how everything works.

1. Database Connection (`[[databases]]`)

    This section tells the system which database to connect to.

    ```toml
    [[databases]]
    name = "sakila"
    uri = "sqlite:///./data/sakila.db"
    schemas_file = "schemas/sakila.py"
    ```

      - `name`: A simple nickname for your database connection.
      - `uri`: The connection uri to your database. We use SQLModel as our ORM, so you can use any [SQLAlchemy-compatible database URI](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls). In this case, we use a SQLite database located at `./data/sakila.db`.
      - `schemas_file`: **(Optional, but Highly Recommended)**
          - This file describes your database structure (tables, columns, etc.) to the AI.
          - **Think of it as a "map" of your data.** By providing a good map, you significantly increase the AI's accuracy in finding the right answers. Without it, the agent will retrieve data from the database, but it may not understand the context or relationships between different pieces of data.
          - We use SQLModel to define the schema, and you can find the example schema file in `schemas/sakila.py`. It includes definitions for tables like `actor`, `customer`, `film`, etc.

2. AI Assistant Server (`[[mcp_servers]]`)

    This section configures the AI assistant itself. It defines what the AI can do and how it should behave.

    ```toml
    [[mcp_servers]]
    name = "sakila"
    llm.model = "gpt-4.1"
    llm.provider= "openai"
    database = "sakila"
    enabled_tools = ["text2sql"]
    description = "..."
    ```

      - `name` & `database`: Links this assistant to the "sakila" database defined above.
      - `llm.provider` & `llm.model`: **Global language model settings**. This sets the default language model provider (e.g., `"openai"`) and the specific model (e.g., `"gpt-4.1"`) for each mcp server.
      - `enabled_tools`: The abilities you give to the AI. `["text2sql"]` means it can translate plain English questions into database queries.
      - `description`: **This is the instruction manual for the AI.** It's the most important setting for controlling the assistant's behavior. It tells the AI:
          - **Its Job**: "You are an assistant for a DVD rental business."
          - **The Rules**: "Only answer questions using the database."
          - **What it can help with**: It lists examples like analyzing sales, customers, or film inventory.


**In short:**

This file sets up an AI assistant that uses **GPT-4.1** to answer questions about the **sample Sakila database**. For the highest accuracy, you should provide a clear **`schemas_file`** to act as a map for the AI, and use the **`description`** to give it clear instructions on its role and limitations.

-----
## Backend Configuration

This configuration file sets up the main backend, which acts as a central router. It determines the default AI model and defines how to connect to and route between different MCP servers (the assistants).

```toml
default_agent="sakila"
llm.provider = "openai"
llm.model = "gpt-4.1"

[[mcp_servers]]
name = "sakila"
host = "127.0.0.1"
port = "8888"
routable_nodes= []
```

### Configuration Explained

This file configures a central routing service that manages one or more AI assistants (MCP Servers).

1.  **Global Settings**

      * `default_agent`: **The default assistant**. This specifies which assistant receives the user's initial request. Its value should correspond to the `name` of an assistant defined in the `[[mcp_servers]]` section below.
      * `llm.provider` & `llm.model`: **Global language model settings**. This sets the default language model provider (e.g., `"openai"`) and the specific model (e.g., `"gpt-4.1"`) for the entire backend. This setting acts as the default for all assistants unless it is overridden in an assistant's specific MCP configuration.

2.  **Connecting to MCP Servers (`[[mcp_servers]]`)**

    This section lists all the AI assistant services that the backend can connect to.

      * `name`: **The unique name of the assistant**. This is used to identify the assistant internally and must match the `name` defined in that assistant's `mcp` configuration.
      * `host` & `port`: **The assistant's network address**. This specifies how the backend service can connect to this MCP assistant, for instance, at `127.0.0.1` (localhost) on port `8888`.
      * `routable_nodes`: **Routable destination assistants**. This is a key routing configuration. It defines which other assistants the current one (in this case, "sakila") can **forward** tasks to.
          * If the list is empty (`[]`), it means this assistant cannot route tasks to any other assistant and must handle them on its own.
          * If you had multiple assistants (e.g., one for database queries and another for web searches), you could define their ability to collaborate here, for example: `routable_nodes = ["search_assistant"]`.


**In short:**

This configuration file sets up a backend that uses **GPT-4.1** as its default model. It registers a single assistant named "sakila," which runs locally, and designates it as the **default handler** for all incoming requests. Crucially, with `routable_nodes` set to empty, the "sakila" assistant will handle all tasks by itself and **will not** forward requests to any other assistants.

-----
