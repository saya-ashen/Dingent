---
sidebar_position: 1
---
# 插件开发

## 快速开始

开发新插件的过程非常简单。首先，您需要一个 Dingent 项目。

### 步骤 1：初始化项目

如果您还没有项目，请参考[安装](../getting-started/installation.md)部分创建一个。

### 步骤 2：创建插件目录

所有插件都位于项目根目录下的 `assistants/plugins/` 目录中。请为您的新插件创建一个专用目录。目录名称应该清楚地描述插件的功能，例如 `greeter` 或 `weather_checker`。

```bash
mkdir -p assistants/plugins/greeter
```

## 插件结构说明

标准的 Dingent 插件包含以下文件结构。每个文件都有特定的用途。

```
assistants/plugins/greeter/
├── __init__.py      # 将目录标记为 Python 包
├── plugin.toml      # 插件的核心元数据和配置
├── settings.py      # 定义插件的可配置选项
├── tool.py          # 插件的主要逻辑实现
└── README.md        # 插件的文档
```

接下来，我们将详细解释每个文件的作用。

### `plugin.toml`（核心配置文件）

这是插件的入口点定义文件。它告诉 Dingent 系统如何加载和使用您的插件。

**示例：**

```toml
[plugin]
# 插件的名称，应该是唯一的
name = "greeter"

# 插件的版本，遵循语义版本控制
version = "1.0.0"

# 指向插件主要逻辑类的引用路径
# 格式是 "filename:ClassName"，指的是 tool.py 中的 Greeter 类
tool_class = "tool:Greeter"

# 插件规范版本
spec_version = 1.0

# 插件运行所需的 Python 依赖项
# 系统将通过 `dingent assistants plugin sync` 命令自动安装这些依赖项
dependencies = [
    "pandas>=2.2.3",
]
```

**字段描述：**

  * `name`：插件的唯一标识符。
  * `version`：插件的当前版本。
  * `tool_class`：指向插件主类的指针，作为逻辑入口点。
  * `spec_version`：您遵循的插件规范版本。
  * `dependencies`：所有必需的第三方 Python 库列表。

### `tool.py`（主要逻辑文件）

此文件包含插件的核心功能代码。您在 `plugin.toml` 中通过 `tool_class` 指定的类就在这里定义。

**关键要求：**

  * 您的主工具类（例如，`Greeter`）**必须**继承自 `dingent.engine.plugins.BaseTool`。

**示例 `tool.py`：**

```python
# tool.py
from typing import Annotated
from pydantic import Field

# 导入核心框架组件
from dingent.engine.plugins import BaseTool
from dingent.engine.resource import ToolOutput, TablePayload

# 从同级 settings.py 文件导入 Settings 类
from .settings import Settings

class Greeter(BaseTool):
    """一个简单的问候工具，演示基本插件结构。"""

    def __init__(
        self,
        config: Settings,
        **kwargs,
    ):
        # 初始化父类，传入配置
        super().__init__(config, **kwargs)
        # self.resource_manager 由系统自动注入，可用于注册资源。

    async def tool_run(
        self,
        target: Annotated[str, Field(description="要问候的人的姓名。")],
    ) -> dict:
        """
        运行工具的核心方法。
        大型语言模型将根据其参数签名和描述决定如何调用此方法。
        """
        # 1. 准备要存储的工具输出内容
        tool_output_payload = TablePayload(
            columns=["greeter", "target"],
            rows=[{"greeter": self.name, "target": target}]
        )

        # 2. 使用资源管理器注册输出并获取 ID
        # 这允许复杂或大型运行结果（如表格或文件）被存储以供稍后显示或分析。
        tool_output_ids = [
            self.resource_manager.register(
                ToolOutput(type="greeter_output", payload=tool_output_payload)
            )
        ]

        # 3. 构建并返回包含三个关键元素的字典
        return {
            "context": f"{self.name} 刚刚向 {target} 问好。",
            "tool_output_ids": tool_output_ids,
            "source": "greeter"
        }
```

#### 代码解释

  * **`__init__(...)`**：构造函数。当框架初始化插件时，它传入用户配置的 `Settings` 对象。系统依赖项如 `resource_manager` 由框架自动注入，无需手动实例化。

  * **`async def tool_run(...)`**：这是工具的执行入口点。

      * **方法参数（`target: Annotated[...]`）**：这些参数直接暴露给大型语言模型（LLM）。模型使用参数的类型提示（`str`）和 `Field` 中的 `description` 来理解如何调用此工具。**清晰准确的 `description` 对于模型正确调用工具至关重要。**

  * **`resource_manager`**：这是系统注入的依赖项。它的核心功能是提供 `register` 方法，允许您将工具的执行结果（例如，表格、图像、代码片段）存储为标准化的 `ToolOutput` 对象。注册返回唯一的资源 ID。

  * **`tool_output_ids`**：这是资源 ID 列表。当您的工具生成需要独立存储和显示的数据（如数据分析表）时，您应该注册它并将生成的 ID 放在此列表中。这使 UI 或其他系统组件能够使用其 ID 获取和显示这些结构化结果。

  * **`return` 字典**：`tool_run` 方法返回包含三个关键字段的结构化字典：

      * `"context"`：此字段的内容是提供给 LLM 生成最终回复的**实际文本**。模型将使用 `context` 来理解工具完成了什么，并制定对用户的响应。它应该是简洁、清晰的事实陈述。
      * `"tool_output_ids"`：返回您刚刚注册的资源 ID 列表。
      * `"source"`：声明此结果的来源，通常是插件的名称。

### `settings.py`（配置文件）

此文件用于定义插件的可配置参数，例如 API 密钥、默认主机地址或行为开关。这允许用户轻松调整插件的行为，而无需修改核心代码。

**关键要求：**

  * 您的配置类**必须**命名为 `Settings` 并继承自 `ToolBaseSettings`。

**示例 `settings.py`：**

```python
# settings.py
from dingent.engine.plugins import ToolBaseSettings

class Settings(ToolBaseSettings):
    """
    Greeter 插件的配置设置。
    这里定义的字段将成为插件初始化期间的必需参数。
    """
    greeterName: str
```

## 依赖管理

在开发插件时，您可能会使用第三方库（例如，`requests`、`pandas`）。您应该将这些库添加到 `plugin.toml` 文件中的 `dependencies` 列表中。

完成开发或更新依赖项后，在**项目根目录**中运行以下命令：

```bash
dingent assistants plugin sync
```

此命令将自动扫描 `assistants/plugins/` 目录中的所有插件，读取其 `plugin.toml` 文件，并将所有声明的依赖项安装到您当前的环境中。这确保了插件的一致运行时环境。