---
sidebar_position: 1
description: How to install Dingent locally, and start an agent project in no time.
---

# Installation

:::tip

Use the **[Fast Track](intro.md#fast-track)** to understand Docusaurus in **5 minutes ⏱**!

:::

## Requirements
- [**uv**](https://docs.astral.sh/uv/getting-started/installation/): A very fast Python package installer and resolver.
    - UV is used to install the Dingent CLI and manage Python dependencies.
- [**Node.js**](https://nodejs.org/en/download/) version 18.0 or above (which can be checked by running node -v). You can use [nvm](https://github.com/nvm-sh/nvm) to manage multiple Node.js versions on a single machine.
- [**bun**](https://bun.com/docs/installation): An all-in-one toolkit for JavaScript and TypeScript applications.
    - Bun is used to manage frontend dependencies and run the development server.
## Scaffold Project
The easyest way to get started is to use the Dingent CLI to scaffold a new project. This will create a fully functional agent project with all the necessary dependencies and configurations.

```bash
uvx dingent init basic
```
This will prompt you for a project name, author, etc., and then automatically create the project directory and install all frontend and backend dependencies.
Then you can navigate to the project directory and start the agent.

## Project Structure
If you chose the `basic` template and named your project `my-awesome-agent`, the project structure will look like this:
```
├── 📄 README.md
├── 🖥️ frontend/
│   ├── src/
│   │   ├── app/
│   │   └── components/
│   └── package.json
├── ⚙️ backend/
│   ├── main.py
│   ├── config.toml
│   └── langgraph.json
└── 🛠️ mcp/
    ├── main.py
    ├── config.toml
    ├── data/
    ├── custom_tools/
    └── schemas/
```
### Overview of Each Part
- frontend: This is the part you see and interact with in your browser.

- backend: This is the project's brain, a Python service.

- assistants:

## Running the development server
To run the development server, you need to set the `OPENAI_API_KEY` environment variable and then run the `dingent run` command.

```bash
# On macOS and Linux
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxx # Replace with your OpenAI API Key

# On Windows (PowerShell)
$env:OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxx" # Replace with your OpenAI API Key
uvx dingent run # Must be run in the project directory
```
