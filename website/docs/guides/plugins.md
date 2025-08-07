---
sidebar_position: 1
---
# Plugin

## **概念：工具 (Tool / Plugin)**

在 Dingent 框架中，一个\*\*工具（Tool）**或**插件（Plugin）\*\*是系统可以执行的最小功能单元。您可以把它想象成智能体（Agent）的一项具体技能。例如：

  * 一个可以**查询天气**的工具。
  * 一个可以**发送邮件**的工具。
  * 一个可以**执行数据库查询**的工具。
  * 一个可以像我们之前例子中一样**打招呼**的工具。

每个工具都由开发者创建，封装了与外部世界交互或执行特定计算的逻辑。作为用户，您的主要任务是在助手的配置中启用和配置这些工具，以满足您的具体需求。

## **如何使用工具？**

在新的配置模式下，您不再需要一个独立的工具配置文件。相反，工具的配置是直接在将要使用它的\*\*助手（Assistant）\*\*内部完成的。

管理和使用插件的流程如下：

1.  **获取插件**：由开发者编写，或由您从社区下载，并放置在项目的 `assistants/plugins` 目录下。
2.  **查看可用插件**：您可以使用命令行工具来查看当前所有已加载的、可供使用的插件。
    ```bash
    dingent assistants plugin list
    ```
3.  **在助手中配置插件**：在助手的配置文件中，为您想要使用的插件填写具体的配置。您可以在下方的“助手”文档中看到详细示例。

-----

# Assistant

## **概念：助手 (Assistant)**

一个**助手（Assistant）是一个面向特定领域任务的工具集合**。

如果说“工具”是一把螺-丝刀或一个扳手，那么“助手”就是一个为特定工作（如“修理电脑”或“组装家具”）而准备的完整**工具箱**。它不仅包含了完成任务所需的工具，还包含了关于如何执行任务的**高级指令**。

例如，您可以创建：

  * **通用聊天助手**: 配置了“打招呼”、“天气查询”、“网络搜索”等工具。
  * **数据分析助手**: 直接在配置中集成了“数据库连接”、“SQL执行”等一系列专业工具。
  * **客户服务助手**: 包含了“订单查询”、“知识库检索”、“创建工单”等工具的配置。

作为用户，您可以通过定义不同的助手，来创建多个具有不同能力和个性的智能体。

## **如何配置助手？**

您可以在一个独立的 `TOML` 配置文件中定义一个或多个助手。每个助手的配置主要包括它的基本信息（如名称）、行为指令，以及它被授权使用的**工具及其详细配置**。

我们推荐使用 `.toml` 格式来管理您的助手配置，因为它能清晰地表述复杂的嵌套结构。

**配置文件示例**

  * **文件位置**: `<此处填写用户配置助手的文件路径，例如：config/assistants.toml>`

<!-- end list -->

```toml
# "[[assistants]]" 定义了一个具体的助手实例
# 您可以在同一个文件中定义多个 [[assistants]] 块

[[assistants]]
name = "sakila"
host = "127.0.0.1"
port = "8888"
description = """
This assistant can only answer questions about the operations of a DVD rental business stored in the database. The query should be about analyzing business performance, customer behavior, or film inventory.

Use this tool for questions about:
- Sales & Revenue: Find sales figures, total revenue for stores or films, and details about specific payments.
- Customer Analysis: Inquire about customer rental habits, find top customers, or analyze customer demographic data like their location.
- Film & Inventory: Find films by title, genre (category), or actor. Check inventory levels for a specific film at a particular store.
- Store & Staff Operations: Explore information about individual stores, their staff, and the rental transactions they process.
"""

# "tools" 列表直接定义和配置该助手可用的工具
tools = [
  {
    type = "text2sql",
    name = "sakila_text2sql",
    description = "A tool to translate natural language questions into SQL queries for the Sakila database.",

    # --- 特定于 text2sql 类型的配置 ---
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
# ... 更多助手的配置 ...
```

#### **配置字段详解**

  * `name` (必需): 您为这个助手设定的唯一名称。
  * `host` (可选): 用于暴露该助手服务的IP地址。
  * `port` (可选): 用于暴露该助手服务的端口。
  * `description` (必需): 对这个助手功能的详细描述。这部分内容也作为给大模型的**核心指令**（System Prompt），模型将严格遵循这里的指示来行动，这决定了它的性格、行为准则和任务目标。您可以使用 `"""` 来输入多行文本。
  * `tools` (必需): 一个列表，其中**直接定义并配置**了这个助手被授权使用的所有工具。
      * 这是一个配置对象的列表，而不是简单的ID列表。
      * 每个工具对象内部的字段（如 `type`, `name`, `llm`, `database` 等）由其插件类型决定。
      * 您需要查阅具体插件的 `README.md` 或相关文档，来了解它有哪些可配置的参数以及如何填写。
