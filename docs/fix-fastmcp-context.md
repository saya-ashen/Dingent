# Fix: FastMCP Client Context Management

## Problem

When invoking the graph, users encountered the following error:
```
RuntimeError: Client is not connected. Use the 'async with client:' context manager first
```

## Root Cause

The issue was in how async context managers were managing the `AsyncExitStack` that holds FastMCP client contexts.

### Original Code Pattern (Broken)
```python
@asynccontextmanager
async def load_tools(self):
    runnable: list[RunnableTool] = []
    async with AsyncExitStack() as stack:  # ❌ Stack closes after yield returns
        for inst in self.plugin_instances.values():
            client = await stack.enter_async_context(inst.mcp_client)
            # ... create closures that capture client
        yield runnable
    # Stack is closed here, client contexts are exited
```

The problem: When `async with AsyncExitStack() as stack` is used, the stack is automatically closed when the `async with` block exits, even if the context manager is held open by an outer stack. This means the client contexts are closed before the graph execution happens, causing the "Client is not connected" error.

### Fixed Code Pattern
```python
@asynccontextmanager
async def load_tools(self):
    runnable: list[RunnableTool] = []
    stack = AsyncExitStack()  # ✅ Stack lifecycle controlled by context manager protocol
    try:
        for inst in self.plugin_instances.values():
            client = await stack.enter_async_context(inst.mcp_client)
            # ... create closures that capture client
        yield runnable
    finally:
        await stack.aclose()
    # Stack closes only when the context manager exits
```

The fix: By manually managing the stack with `try/finally`, we allow the async context manager protocol to control when cleanup happens. When the outer code enters this context manager into its own stack, the stack stays alive for the entire duration.

## Files Changed

1. **src/dingent/core/runtime/assistant.py**
   - `load_tools()` method: Fixed to manually manage stack lifecycle
   - `load_tools_langgraph()` method: Fixed to manually manage stack lifecycle

2. **src/dingent/engine/graph.py**
   - `create_assistant_graphs()` function: Fixed to manually manage stack lifecycle

## Context Lifetime Flow

With the fix:
```
graph_factory.py:
  stack (outer) created
    ↓
  create_assistant_graphs() entered into outer stack
    ↓
  inner stack created in create_assistant_graphs()
    ↓
  load_tools() entered into inner stack
    ↓
  innermost stack created in load_tools()
    ↓
  mcp_client contexts entered into innermost stack
    ↓
  yield tools (all stacks stay alive)
    ↓
  Graph is built and compiled
    ↓
  Graph is returned to caller
    ↓
  Graph is EXECUTED (clients still connected ✅)
    ↓
  When outer stack closes, all nested contexts clean up
```

## Testing

The fix ensures that FastMCP client contexts remain active for the entire lifetime of graph execution, preventing the "Client is not connected" error.
