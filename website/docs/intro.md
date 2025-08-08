---
sidebar_position: 1
---

# Introduction

## Highlights
* **No More Repetition**: We package the best practices for backend services (LangGraph), data interfaces (Assistant), and frontend presentation (CopilotKit) into a single command. You no longer need to build everything from scratch and can start writing your core business logic immediately.

* **Core Features Built-In**: We believe a simple and easy-to-use agent shouldn't require users to spend a lot of time maintaining plugins. Therefore, we are committed to integrating features the community deems important directly into the framework. If you think a feature is crucial, we encourage you to open an Issue or PR. This directly reflects our core mission of "making Agents simpler for users."

* **Focused, Not Comprehensive**: Unlike other general-purpose Agent frameworks, Dingent specializes in data retrieval and Q\&A scenarios, offering a more lightweight and focused solution.

* **Smooth Learning Curve**: You only need a basic understanding of Python and some frontend knowledge to build powerful applications, without needing to be an expert in LangGraph or FastAPI. At the same time, we retain the flexibility to expand functionalities, ensuring the framework can fully support custom development when needed.

## Fast Track

Create a fully functional agent project from scratch in just a few minutes.


Install [**uv**](https://docs.astral.sh/uv/getting-started/installation/) and [**Node.js**](https://nodejs.org/en/download/) in your development environment, and create a new project use the template we provided.

```bash
# Use the 'basic' template to create a new project
uvx dingent init basic
```

Start the agent.
```bash
cd my-awesome-agent # Navigate to your project directory

# On macOS and Linux
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxx # Replace with your OpenAI API Key

# On Windows (PowerShell)
$env:OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxx" # Replace with your OpenAI API Key

uvx dingent run
```

Open  [http://localhost:3000](http://localhost:3000) and follow the tutorial.

## Your First Conversation
