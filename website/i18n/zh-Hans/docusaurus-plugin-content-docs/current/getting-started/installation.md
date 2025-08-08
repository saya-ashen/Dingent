---
sidebar_position: 1
description: 如何在本地安装 Dingent，并快速启动一个智能体项目。
---

# 安装

:::tip

使用 **[快速开始](../intro.md#快速开始)** 在 **5 分钟内⏱** 了解 Dingent！

:::

## 环境要求
- [**uv**](https://docs.astral.sh/uv/getting-started/installation/): 一个非常快的 Python 包安装和解析工具。
    - UV 用于安装 Dingent CLI 和管理 Python 依赖项。
- [**Node.js**](https://nodejs.org/en/download/) 版本 18.0 或更高（可通过运行 node -v 查看）。您可以使用 [nvm](https://github.com/nvm-sh/nvm) 在单台机器上管理多个 Node.js 版本。
- [**bun**](https://bun.com/docs/installation) **\[可选\]**: 一个适用于 JavaScript 和 TypeScript 应用程序的一体化工具包。
    - Bun 用于管理前端依赖项和运行开发服务器。您可以使用 npm 或 yarn 代替，但我们推荐 bun 因为它的速度和简洁性。

## 脚手架项目
开始的最简单方法是使用 Dingent CLI 来搭建新项目。这将创建一个功能齐全的智能体项目，包含所有必要的依赖项和配置。

```bash
uvx dingent[cli] init basic
```

这将提示您输入项目名称、作者等信息，然后自动创建项目目录并安装所有前端和后端依赖项。
然后，您可以导航到项目目录并启动智能体。

## 项目结构
如果您选择了 `basic` 模板并将项目命名为 `my-awesome-agent`，项目结构将如下所示：

```
my-awesome-agent/
├── 📁 backend/       # 后端服务（基于 FastAPI 和 LangGraph）
├── 📁 frontend/      # 前端应用（基于 CopilotKit）
├── 📁 assistants/    # 面向特定领域任务的工具集合
└── 📄 README.md      # 项目文档
```

### 各部分概述
- **frontend/**: 这是您在浏览器中看到和交互的部分。它使用现代 Web 技术构建，提供直观的聊天界面。
- **backend/**: 这是项目的大脑，一个 Python 服务，编排智能体的逻辑，处理请求，并与 LLM 协调。
- **assistants/**: 这包含您的智能体可以用来执行任务的工具和数据源。它包括自定义插件、数据文件和服务配置。

## 运行开发服务器
要运行开发服务器，您需要设置 `OPENAI_API_KEY` 环境变量，然后运行 `dingent run` 命令。

```bash
cd my-awesome-agent

# 在 macOS 和 Linux 上
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxx # 替换为您的 OpenAI API Key

# 在 Windows (PowerShell) 上
$env:OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxx" # 替换为您的 OpenAI API Key

uvx dingent run # 必须在项目目录中运行
```

默认情况下，Dingent 会启动一个 LangGraph 后端服务和 Assistants 服务，并在浏览器中打开前端界面。
如果前端没有自动打开，您可以手动访问 [http://localhost:3000](http://localhost:3000)。