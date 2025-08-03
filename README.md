<div align="center"><a name="readme-top"></a>

# Dingent

  <strong>A lightweight, user-friendly LLM Agent framework focused on simplifying data retrieval application development.</strong>

![GitHub Release Date](https://img.shields.io/github/release-date/saya-ashen/Dingent)
![GitHub License](https://img.shields.io/github/license/saya-ashen/Dingent)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/saya-ashen/Dingent/publish-pypi.yml)
![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/saya-ashen/Dingent)
![PyPI - Version](https://img.shields.io/pypi/v/dingent)

**English** · [简体中文](./README.zh-CN.md)

</div>

**Dingent** is a lightweight, user-friendly agent framework whose core goal is to simplify the creation process of data applications based on Large Language Models (LLMs). We provide a concise yet powerful toolkit, with the key highlight being the ability to automatically connect to databases. This enables you to quickly link your database with an LLM to build applications capable of intelligent Q\&A, data extraction, and analysis. For other data sources like APIs and local documents, Dingent offers a flexible framework that developers can easily integrate by writing custom code.

## 🎯 Why Choose Dingent?

When building LLM data applications, developers often spend a significant amount of time on "glue code": connecting to databases, wrapping APIs, setting up frontend-backend communication... These tasks are tedious and repetitive.

**The core value of Dingent lies in:**

  * **Avoiding Repetition**: We've bundled the best practices for backend services (LangGraph), data interfaces (MCP), and frontend presentation (CopilotKit) into a single command. You no longer need to set them up manually and can start writing your core business logic immediately.

  * **Focused, Not Comprehensive**: Unlike other general-purpose Agent frameworks, Dingent specializes in data retrieval and Q\&A scenarios, offering a more lightweight and focused solution.

  * **Smooth Learning Curve**: You only need to know Python and some basic frontend concepts. You don't have to be an expert in LangGraph or FastAPI to build powerful applications.

## ✨ Features

  * **One-Command Project Initialization**: Use the `uvx dingent[cli] init` command to quickly generate a complete project structure—including frontend, backend, and core logic—from a template.
  * **Lightweight and Easy-to-Use**: Simple design with a gentle learning curve, allowing you to focus on business logic rather than tedious configuration.
  * **Focused on Data Retrieval**: Specially optimized for scenarios like data Q\&A, extraction, and analysis, providing efficient solutions.
  * **Flexible Data Source Integration**: Easily integrate various data sources such as APIs, databases, and files (PDF, Markdown, etc.).
  * **LLM-Powered**: Seamlessly connect with mainstream LLMs like the OpenAI GPT series, local models, and more.

## 🚀 Quick Start

Create a full-featured agent project from scratch in just a few minutes.

### 1. Prerequisites

Before you begin, ensure you have `uv` and `bun` installed in your development environment.

  * **uv**: An extremely fast Python package installer and resolver.

    ```bash
    # On macOS and Linux.
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

    ```bash
    # On Windows.
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

  * **Bun**: An all-in-one toolkit for JavaScript and TypeScript applications.

    ```bash
    # On macOS and Linux.
    curl -fsSL https://bun.com/install | bash
    ```

    ```bash
    # on Windows
    powershell -c "irm bun.com/install.ps1 | iex"
    ```

### 2. Initialize Your Agent Project

Execute the following command. The Dingent CLI will guide you through the project creation process.

```bash
uvx dingent[cli] init basic # Create a basic project using the 'basic' template
```

The CLI will prompt you for information like the project name and author, then automatically create the project directory and install all frontend and backend dependencies.

### 3. Launch and Develop

Once the project is created, navigate to the project directory:

```bash
cd my-awesome-agent
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxx # Replace with your OpenAI API Key
uvx dingent run
```

By default, Dingent will start a LangGraph backend service and an MCP service, and open the frontend interface in your browser.
If the frontend doesn't open automatically, you can manually visit [http://localhost:3000](https://www.google.com/search?q=http://localhost:3000) to view it.

Your project skeleton is now ready\! You can:

  * **Explore the project structure**: See the `🏛️ Project Architecture` section below to understand the directory layout.
  * **Develop the backend logic**: Edit the Python files in the `mcp/` and `backend/` directories to implement your core agent logic and APIs.
  * **Develop the frontend interface**: Build your user interface in the `frontend/` directory.

## 🏛️ Project Architecture

The project generated by the `init` command has a standardized structure, making collaboration and maintenance easier:

```plaintext
my-awesome-agent/
├── 📁 backend/         # Backend service (based on FastAPI and LangGraph)
├── 📁 frontend/        # Frontend application (based on CopilotKit)
├── 📁 mcp/             # Model Context Protocol (MCP) service
└── 📄 README.md        # Project's README file
```

### 📦 backend/

  * The backend service is the core coordinator of the application, built with FastAPI and [LangGraph](https://www.langchain.com/langgraph).

  * **Primary Responsibilities**: Handles requests from the frontend, orchestrates and executes the agent's core logic, interacts with the LLM and MCP service, and returns results to the frontend.

  * **Files**: `main.py` is the service entry point. Here, you can define API routes and the agent's execution flow. For details, refer to the [LangGraph documentation](https://langchain-ai.github.io/langgraph).

### 📦 frontend/

  * The frontend is a modern web interface built with [CopilotKit](https://docs.copilotkit.ai) and Bun, responsible for all user interactions.

  * **Primary Responsibilities**: Provides an interface for user queries and displays streaming responses from the agent, including data tables, Markdown, and other formats.

  * **Files**: The core page logic is located in `src/app/page.tsx`, and UI components are in `src/components/`.

### 📦 mcp/

  * The MCP (Model Context Protocol) service acts as the "gateway" for your data and tools, hailed as "the USB-C port for AI." It provides a unified, secure interface for LLM applications to access the resources you define. For a detailed introduction, please refer to [FastMCP](https://gofastmcp.com/getting-started/welcome).

  * **Primary Responsibilities**: Exposes data and functions to the Agent in the `backend/`.

  * **Files**:

      * `data/`: Stores your data source files (e.g., .db, .csv, .md).
      * `custom_tools/`: Defines custom tools that can be called by the Agent.
      * `main.py`: Starts the MCP service and registers the resources and tools mentioned above.

## Detailed Usage

Coming soon.

## 🗺️ Roadmap

  * [ ] Comprehensive documentation and tutorials.
  * [ ] Integration with popular vector databases.
  * [ ] More project templates (e.g., a template specifically for knowledge base Q\&A).

## 🤝 How to Contribute

We warmly welcome contributions from the community\! If you are interested, please follow these steps:

1.  **Fork** this repository.
2.  Create a new feature branch (`git checkout -b feature/YourAmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push your branch to GitHub (`git push origin feature/YourAmazingFeature`).
5.  Create a **Pull Request**.

We also welcome bug reports and feature suggestions of any kind. Please submit them via [GitHub Issues](https://github.com/saya-ashen/Dingent/issues).

## 📄 License

This project is licensed under the [MIT License](https://www.google.com/search?q=./LICENSE).
