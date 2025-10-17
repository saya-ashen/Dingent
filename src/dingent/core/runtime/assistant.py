from __future__ import annotations

"""
Assistant runtime container that wires together enabled plugin runtimes and
exposes their MCP tools as lightweight, runnable callables.

Design notes:
- `load_tools()` opens and closes an MCP connection per call to keep resource
  usage low when the caller enumerates tools then calls one occasionally.
  context using `AsyncExitStack`, which is more efficient for burst workloads.
"""

from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

from dingent.core.db.models import Assistant
from dingent.core.schemas import RunnableTool

from ..managers.plugin_manager import PluginManager
from .plugin import PluginRuntime


class AssistantRuntime:
    """Holds assistant metadata and live plugin runtimes.

    This runtime represents an instantiated Assistant with a set of enabled
    plugin runtimes and provides utilities to list and invoke MCP tools.

    Attributes:
        id (str): Assistant identifier.
        name (str): Assistant display name.
        description (str): Optional description of the assistant.
        plugin_instances (dict[str, PluginRuntime]): Live plugin runtimes keyed
            by their registry_id.
        destinations (list[str]): Downstream assistant names/IDs reachable in
            the active workflow (set by the workflow layer).
        _log_method (Callable): Logging function `(level, message, **context)`.
    """

    def __init__(
        self,
        assistant_id: str,
        name: str,
        log_method: Callable,
        description: str,
        plugin_instances: dict[str, PluginRuntime],
        plugin_configs: dict[str, dict[str, Any]] | None = None,
    ):
        """Initialize the runtime with metadata and plugin instances.

        Args:
            assistant_id: Unique ID of the assistant.
            name: Human-readable assistant name.
            log_method: Logging callable used by this runtime.
            description: Optional textual description.
            plugin_instances: Mapping of registry_id -> PluginRuntime.
            plugin_configs: Optional per-plugin config (not used here).
        """
        self.id = assistant_id
        self.name = name
        self.description = description
        self.plugin_instances = plugin_instances
        self.destinations: list[str] = []
        self._log_method = log_method
        # NOTE: plugin_configs is accepted for future use but not stored to avoid
        # duplicating configuration responsibilities at multiple layers.

    @classmethod
    async def create_runtime(
        cls,
        plugin_manager: PluginManager,
        assistant: Assistant,
        log_method: Callable,
    ) -> AssistantRuntime:
        """Factory: build a runtime by materializing enabled plugin instances.

        Iterates over enabled plugin links, ensures a PluginRuntime exists for
        each (via the PluginManager), and collects them into this runtime.

        Args:
            plugin_manager: Manager that creates/caches PluginRuntime objects.
            assistant: Assistant ORM object including `plugin_links`.
            log_method: Logging callable used for diagnostic messages.

        Returns:
            AssistantRuntime: A fully constructed runtime.

        Notes:
            - Failures to init a specific plugin are logged and skipped so one
              bad plugin does not prevent the assistant from running.
        """
        plugin_instances: dict[str, PluginRuntime] = {}
        enabled_plugins = [p for p in assistant.plugin_links if p.enabled]
        for link in enabled_plugins:
            manifest = link.plugin
            try:
                inst = await plugin_manager.get_or_create_runtime(manifest.registry_id)
                plugin_instances[manifest.registry_id] = inst
            except Exception as e:
                # Log and continue; this isolates failures per plugin.
                log_method(
                    "error",
                    "Create plugin instance failed (assistant={name} plugin={pid}): {e}",
                    context={"name": assistant.name, "pid": link.plugin_id, "e": e},
                )
                continue
        return cls(
            str(assistant.id),
            assistant.name,
            log_method,
            assistant.description or "",
            plugin_instances,
        )

    @asynccontextmanager
    async def load_tools(self):
        """Temporarily load MCP tools as runnable callables.

        Opens a short-lived MCP client per plugin only to enumerate tools, and
        **re-opens** the connection on each tool invocation. Favor this if:
        - you list tools and call only a few; or
        - you want minimal connection residency.

        Yields:
            list[RunnableTool]: Each item wraps a tool spec and a `run(arguments)`
            coroutine that re-opens the underlying MCP client.

        Example:
            >>> async with (
            ...     runtime.load_tools() as tools
            ... ):
            ...     for t in tools:
            ...         if (
            ...             t.tool.name
            ...             == "my_tool"
            ...         ):
            ...             result = await t.run(
            ...                 {
            ...                     "x": 1
            ...                 }
            ...             )
        """
        runnable: list[RunnableTool] = []
        for inst in self.plugin_instances.values():
            # Short-lived open to enumerate tools; avoids holding many connections.
            async with inst.mcp_client as client:
                tools = await client.list_tools()

            for t in tools:
                # Bind `inst` and `t` at definition time via default args to avoid
                # late-binding closure traps in loops.
                async def call_tool(arguments: dict, _runtime=inst, _tool=t):
                    # Re-open for the actual call; ensures fresh connection/state.
                    async with _runtime.mcp_client as tool_client:
                        return await tool_client.call_tool(_tool.name, arguments=arguments)

                runnable.append(RunnableTool(tool=t, run=call_tool))
        yield runnable

    async def aclose(self):
        """Load MCP tools with connections held for the whole context.

        Keeps all plugin MCP connections open using `AsyncExitStack`, then
        invokes tools over those persistent clients. Prefer this for bursty
        workloads that will issue many tool calls in a short period.

        Yields:
            list[RunnableTool]: Runnable tools whose `run()` uses the already
            opened clients (lower overhead per call).

        Warning:
            Holding connections may increase server resource usage; ensure the
            context is kept as short as practical.
        """
        for inst in self.plugin_instances.values():
            try:
                await inst.aclose()
            except Exception as e:
                self._log_method("warning", "Error closing plugin instance (assistant={name}): {e}", context={"name": self.name, "e": e})
        self.plugin_instances.clear()
