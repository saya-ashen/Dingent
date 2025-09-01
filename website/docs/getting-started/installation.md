---
sidebar_position: 2
description: How to install Dingent locally, and start an agent project in no time.
---

# Installation

:::tip

Use the **[Fast Track](./introduction.md#fast-track)** to understand Docusaurus in **5 minutes ⏱**!

:::


# Installation

This guide will walk you through installing the Dingent framework and its command-line interface (CLI). With just a few commands, you'll have everything you need to start building your first agent.

## Prerequisites

Before installing Dingent, please ensure your development environment meets the following requirements:


### 1. uv

We use `uv`, a high-performance Python package installer, to create projects and manage dependencies. It simplifies the setup process significantly.

Install `uv` by running the command for your operating system:

**On macOS and Linux:**

```bash
curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh
```

**On Windows:**

```powershell
powershell -ExecutionPolicy ByPass -c "irm [https://astral.sh/uv/install.ps1](https://astral.sh/uv/install.ps1) | iex"
```

After installation, close and reopen your terminal to ensure `uv` is in your system's PATH.

## Installing the Dingent CLI

The `dingent` command-line tool is the primary way to create, manage, and run your projects. The recommended way to use it is with `uvx`, which automatically downloads and runs the latest version without requiring a permanent installation.

This approach ensures you are always using the most up-to-date version of the framework when starting a new project.

## Verifying the Installation

To confirm that everything is set up correctly, run the following command in your terminal:

```bash
uvx dingent --help
```

If the installation was successful, you should see the Dingent help message, like this:

```
 Usage: dingent [OPTIONS] COMMAND [ARGS]...

 Dingent Agent Framework CLI

╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.                                                     │
│ --show-completion             Show completion for the current shell, to copy it or customize the installation.              │
│ --help                        Show this message and exit.                                                                   │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ run       Concurrently starts the backend and frontend services.                                                            │
│ dev       Starts the development server, primarily for debugging the backend Graph and API.                                 │
│ init      Create a new Agent project from a template.                                                                       │
│ version   Show the Dingent version                                                                                          │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

If you see an error, please double-check that `uv` was installed correctly in the prerequisite step.

## Next Steps (下一步)

Congratulations, you have successfully installed Dingent\!

You are now ready to create your first agent project. Let's move on to the next guide to learn about the project structure and how to get your agent running.

➡️ **Next: [Project Structure](./project-structure.md)**
