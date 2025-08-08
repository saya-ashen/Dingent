---
sidebar_position: 1
---

# 介绍

## 亮点
* **拒绝重复**: 我们将后端服务 (LangGraph)、数据接口 (MCP) 和前端展示 (CopilotKit) 的最佳实践打包成一个命令。你无需再手动搭建，可以立即开始编写核心业务逻辑。

* **内置核心功能**: 我们认为，一个简单易用的智能体，不应该让用户花费大量时间维护插件。因此，我们致力于将社区认为重要的功能直接内置到框架中。如果你认为某个功能很重要，我们鼓励你提出 Issue 或 PR，这直接体现了我们"让用户更简单地使用 Agent"的核心使命。

* **专注而非全面**: 与其他通用型 Agent 框架不同，Dingent 专注于数据检索与问答场景，提供了更轻量、更聚焦的解决方案。

* **平滑的学习曲线**: 你只需要了解 Python 和一些基本的前端知识，无需成为 LangGraph 或 FastAPI 的专家就能构建出强大的应用。同时，我们也保留了快速拓展功能的灵活性，保证用户在需要时，该框架能完全胜任个性化功能的开发。

## 快速开始

在几分钟内，从零开始创建一个功能完备的智能体项目。

在您的开发环境中安装 [**uv**](https://docs.astral.sh/uv/getting-started/installation/) 和 [**Node.js**](https://nodejs.org/en/download/)，然后使用我们提供的模板创建新项目。

```bash
# 使用 'basic' 模板创建新项目
uvx dingent[cli] init basic
```

启动智能体。
```bash
cd my-awesome-agent # 导航到您的项目目录

# 在 macOS 和 Linux 上
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxx # 替换为你的 OpenAI API Key

# 在 Windows (PowerShell) 上
$env:OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxx" # 替换为你的 OpenAI API Key

uvx dingent run
```

打开 [http://localhost:3000](http://localhost:3000) 并按照教程进行操作。