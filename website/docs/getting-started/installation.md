---
sidebar_position: 1
description: How to install Dingent locally, and start an agent project in no time.
---

# Installation

:::tip

Use the **[Fast Track](../intro.md#fast-track)** to understand Dingent in **5 minutes ⏱**!

:::

## Requirements
- [**uv**](https://docs.astral.sh/uv/getting-started/installation/): A very fast Python package installer and resolver.
    - UV is used to install the Dingent CLI and manage Python dependencies.
- [**Node.js**](https://nodejs.org/en/download/) version 18.0 or above (which can be checked by running node -v). You can use [nvm](https://github.com/nvm-sh/nvm) to manage multiple Node.js versions on a single machine.
- [**bun**](https://bun.com/docs/installation) **\[Optional\]**: An all-in-one toolkit for JavaScript and TypeScript applications.
    - Bun is used to manage frontend dependencies and run the development server. You can use npm or yarn instead, but we recommend bun for its speed and simplicity.

## Scaffold Project
The easiest way to get started is to use the Dingent CLI to scaffold a new project. This will create a fully functional agent project with all the necessary dependencies and configurations.

```bash
uvx dingent[cli] init basic
```

This will prompt you for a project name, author, etc., and then automatically create the project directory and install all frontend and backend dependencies.
Then you can navigate to the project directory and start the agent.

## Project Structure
If you chose the `basic` template and named your project `my-awesome-agent`, the project structure will look like this:

```
my-awesome-agent/
├── 📁 backend/       # Backend service (based on FastAPI and LangGraph)
├── 📁 frontend/      # Frontend application (based on CopilotKit)
├── 📁 assistants/    # A collection of tools for specific domain tasks
└── 📄 README.md      # The project's documentation
```

### Overview of Each Part
- **frontend/**: This is the part you see and interact with in your browser. It's built with modern web technologies and provides an intuitive chat interface.
- **backend/**: This is the project's brain, a Python service that orchestrates the agent's logic, handles requests, and coordinates with LLMs.
- **assistants/**: This contains tools and data sources that your agent can use to perform tasks. It includes custom plugins, data files, and service configurations.

## Running the development server
To run the development server, you need to set the `OPENAI_API_KEY` environment variable and then run the `dingent run` command.

```bash
cd my-awesome-agent

# On macOS and Linux
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxx # Replace with your OpenAI API Key

# On Windows (PowerShell)
$env:OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxx" # Replace with your OpenAI API Key

uvx dingent run # Must be run in the project directory
```

By default, Dingent will start a LangGraph backend service and an Assistants service, and open the frontend interface in your browser.
If the frontend doesn't open automatically, you can manually visit [http://localhost:3000](http://localhost:3000).
