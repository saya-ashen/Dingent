"""
tool_wrapper.py

为插件作者提供一个统一的工具包装器 (decorator)，
把任意原始函数返回值标准化成框架中间件可识别的结构：
{
  "model_text": "...",
  "display": [ { "type": "...", ... }, ... ],
  "data": <原始或结构化数据>,
  "metadata": {...}
}

中间件(ResourceMiddleware) 会把此结构转换为 ToolResult 并只向模型注入 model_text，
前端通过 tool_output_id 拉取完整展示数据。

核心能力：
1. 自动推断展示类型 (display="auto")：
   - list[dict] / list[BaseModel] / list[dataclass]  -> table
   - dict -> 单行 table 或 markdown (按复杂度)
   - str  -> markdown
   - 其他 -> repr() markdown
2. 支持显式指定展示类型 display="table"/"markdown" 或 display=["table","markdown"]。
3. 支持对 list[dict] 进行列合并、截断、统计元数据。
4. 自动生成 model_text（可自定义 summarizer）。
5. 可配置最大行数、列顺序、是否附带原始数据、是否转储为 table。
6. 保持 sync / async 函数兼容。
7. 避免模型注入过大数据（model_text 自动压缩到指定字符上限）。

示例：
    from tool_wrapper import tool

    @tool(display="table", table_title="用户列表", max_table_rows=50)
    def list_users():
        return [
            {"id": 1, "name": "Alice", "role": "admin"},
            {"id": 2, "name": "Bob", "role": "user"},
        ]

    @tool(display="auto")
    async def fetch_summary():
        return {
            "stats": {"success": 20, "failed": 2},
            "detail": "任务执行完成"
        }

    # 返回结果直接是标准 dict，框架中间件会识别
"""

from __future__ import annotations

import inspect
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, is_dataclass
from typing import Any

try:
    # 依赖于前面你改造后的 types.py
    from .types import MarkdownPayload, TablePayload, ToolResult
except Exception:  # 插件内部相对导入失败时，也允许本地测试
    from types import MarkdownPayload, TablePayload, ToolResult  # type: ignore


# ---------------------------
# 类型别名
# ---------------------------
SummarizerFn = Callable[[Any, dict], str]


def default_summarizer(data: Any, ctx: dict) -> str:
    """
    默认摘要生成逻辑。
    ctx 可能包含:
      - output_kinds: list[str]
      - row_count / truncated / columns
      - original_type
    """
    if "row_count" in ctx and ctx.get("output_kinds") and "table" in ctx["output_kinds"]:
        cols = ctx.get("columns") or []
        col_preview = ", ".join(cols[:6])
        rc = ctx.get("row_count")
        truncated = ctx.get("truncated")
        trunc_note = " (已截断)" if truncated else ""
        return f"表格：{ctx.get('table_title', '')} 共 {rc} 行，列: {col_preview}{trunc_note}".strip()

    # dict 简要
    if isinstance(data, dict):
        keys_preview = ", ".join(list(data.keys())[:10])
        return f"返回字典，键: {keys_preview}"

    # list 简要
    if isinstance(data, list):
        return f"返回列表，长度 {len(data)}，元素类型: {type(data[0]).__name__ if data else 'unknown'}"

    # 纯字符串
    if isinstance(data, str):
        return data[:400]

    return f"返回类型: {type(data).__name__}"


def _is_pydantic_model(obj: Any) -> bool:
    # 兼容 v1 / v2 的粗略判断
    return hasattr(obj, "model_dump") or hasattr(obj, "__fields__")


def _pydantic_to_dict(obj: Any) -> dict:
    try:
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        elif hasattr(obj, "dict"):
            return obj.dict()
    except Exception:
        pass
    return dict(obj.__dict__)


def _normalize_sequence_items(seq: Sequence[Any]) -> list[dict]:
    """
    将 list 中的元素统一转换为 dict（支持 dataclass / pydantic / 普通对象 / 已是 dict）
    """
    norm: list[dict] = []
    for item in seq:
        if item is None:
            norm.append({})
        elif isinstance(item, dict):
            norm.append(item)
        elif is_dataclass(item):
            norm.append(asdict(item))
        elif _is_pydantic_model(item):
            norm.append(_pydantic_to_dict(item))
        else:
            # 尝试提取对象的 __dict__，再降级
            if hasattr(item, "__dict__"):
                try:
                    norm.append({k: v for k, v in vars(item).items() if not k.startswith("_")})
                except Exception:
                    norm.append({"value": repr(item)})
            else:
                norm.append({"value": repr(item)})
    return norm


def _infer_display_types(result: Any) -> list[str]:
    """
    推断合适的展示类型。
    """
    if isinstance(result, str):
        return ["markdown"]
    if isinstance(result, list):
        # 如果是 list 且元素是 dict / dataclass / pydantic，则优先 table
        if not result:
            return ["markdown"]
        first = result[0]
        if isinstance(first, dict) or is_dataclass(first) or _is_pydantic_model(first):
            return ["table"]
        return ["markdown"]
    if isinstance(result, dict):
        # 结构可能复杂，这里返回 markdown + data -> 具体由后续逻辑决定是否转成 table 单行
        return ["markdown"]
    return ["markdown"]


def _build_table_payload(
    rows: list[dict],
    *,
    title: str = "",
    columns: list[str] | None = None,
    max_rows: int = 100,
) -> tuple[TablePayload, dict]:
    """
    构建 TablePayload，并返回 (payload, stats)

    stats: {row_count, truncated, columns}
    """
    # 统计所有字段
    inferred_cols = columns or []
    if not columns:
        col_set = set()
        for r in rows:
            col_set.update(r.keys())
        inferred_cols = list(col_set)

    original_len = len(rows)
    truncated = False
    if original_len > max_rows:
        rows = rows[:max_rows]
        truncated = True

    # 转换为表格行：统一只保留 inferred_cols 中存在的字段
    processed_rows: list[dict] = []
    for r in rows:
        processed_rows.append({c: r.get(c) for c in inferred_cols})

    payload = TablePayload(
        title=title or "",
        columns=inferred_cols,
        rows=processed_rows,
    )
    stats = {
        "row_count": original_len,
        "truncated": truncated,
        "columns": inferred_cols,
        "table_title": title or "",
    }
    return payload, stats


def tool(
    *,
    display: str | list[str] = "auto",
    table_title: str = "",
    table_columns: list[str] | None = None,
    max_table_rows: int = 100,
    include_data: bool = True,
    include_raw_data: bool | None = None,
    summarizer: SummarizerFn | None = None,
    max_model_text_chars: int = 800,
    force_single_row_table_for_dict: bool = True,
    metadata_extra: Callable[[Any, dict], dict] | None = None,
):
    """
    decorator 工厂。

    参数:
        display:
            - "auto": 自动推断
            - "table" / "markdown"
            - ["table","markdown"] 组合 (按顺序生成多个展示)
        table_title: 表格标题
        table_columns: 指定列顺序；为空则自动收集
        max_table_rows: 表格展示最大行数 (超出截断)
        include_data: 是否放入 data 字段 (结构化数据)
        include_raw_data: 若为 None 则与 include_data 同义；若 True 强制放入原始返回
        summarizer: 自定义摘要函数 (data, ctx) -> str
        max_model_text_chars: model_text 最大长度截断
        force_single_row_table_for_dict:
            如果返回 dict 且 display 包含 table，则构建单行表格 (key/value)？
        metadata_extra: 追加 metadata (data, ctx) -> dict
    """
    if include_raw_data is None:
        include_raw_data = include_data

    if isinstance(display, str):
        if display != "auto":
            display_list = [display]
        else:
            display_list = []
    else:
        display_list = list(display)

    def decorator(func: Callable):
        is_async = inspect.iscoroutinefunction(func)

        async def run_async(*args, **kwargs):
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            return _build_tool_result(
                result=result,
                func=func,
                requested_display=display_list,
                auto_display=(display == "auto"),
                table_title=table_title,
                table_columns=table_columns,
                max_table_rows=max_table_rows,
                include_data=include_data,
                include_raw_data=include_raw_data,
                summarizer=summarizer or default_summarizer,
                max_model_text_chars=max_model_text_chars,
                force_single_row_table_for_dict=force_single_row_table_for_dict,
                metadata_extra=metadata_extra,
                elapsed_ms=elapsed,
            )

        def run_sync(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            return _build_tool_result(
                result=result,
                func=func,
                requested_display=display_list,
                auto_display=(display == "auto"),
                table_title=table_title,
                table_columns=table_columns,
                max_table_rows=max_table_rows,
                include_data=include_data,
                include_raw_data=include_raw_data,
                summarizer=summarizer or default_summarizer,
                max_model_text_chars=max_model_text_chars,
                force_single_row_table_for_dict=force_single_row_table_for_dict,
                metadata_extra=metadata_extra,
                elapsed_ms=elapsed,
            )

        if is_async:

            async def wrapper(*args, **kwargs):
                tool_result = await run_async(*args, **kwargs)
                # 返回 dict（这样中间件的 JSON 解析逻辑有效）
                return tool_result

            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper
        else:

            def wrapper(*args, **kwargs):
                tool_result = run_sync(*args, **kwargs)
                return tool_result

            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper

    return decorator


def _build_tool_result(
    *,
    result: Any,
    func: Callable,
    requested_display: list[str],
    auto_display: bool,
    table_title: str,
    table_columns: list[str] | None,
    max_table_rows: int,
    include_data: bool,
    include_raw_data: bool,
    summarizer: SummarizerFn,
    max_model_text_chars: int,
    force_single_row_table_for_dict: bool,
    metadata_extra: Callable[[Any, dict], dict] | None,
    elapsed_ms: float,
) -> dict:
    """
    将原始返回 result 转换成 ToolResult.model_dump()
    """
    original_type = type(result).__name__
    output_payloads: list = []
    ctx: dict = {
        "original_type": original_type,
        "function_name": func.__name__,
        "output_kinds": [],
    }
    data_field: Any = None

    # 1. 自动推断展示类型
    if auto_display:
        inferred = _infer_display_types(result)
        ctx["inferred_display"] = inferred
        display_types = inferred
    else:
        display_types = requested_display

    # 2. 针对不同类型构建展示 payload
    if isinstance(result, str):
        if "markdown" in display_types:
            output_payloads.append(MarkdownPayload(content=result))
            ctx["output_kinds"].append("markdown")
        data_field = result if include_data else None

    elif isinstance(result, list):
        # 如果是 list of dict/对象 -> table
        if "table" in display_types and (result and (isinstance(result[0], dict) or is_dataclass(result[0]) or _is_pydantic_model(result[0]))):
            norm_rows = _normalize_sequence_items(result)
            table_payload, stats = _build_table_payload(
                norm_rows,
                title=table_title or func.__name__,
                columns=table_columns,
                max_rows=max_table_rows,
            )
            output_payloads.append(table_payload)
            ctx.update(stats)
            ctx["output_kinds"].append("table")
            # 同时加一个 markdown (可选)
            if "markdown" in display_types:
                md_text = f"{table_payload.title}：{stats['row_count']} 行，列 {', '.join(stats['columns'])}"
                output_payloads.append(MarkdownPayload(content=md_text))
                ctx["output_kinds"].append("markdown")
            data_field = result if include_data else None
        else:
            # 非结构化列表 -> markdown
            text = "\n".join(repr(x) for x in result[:50])
            if len(result) > 50:
                text += f"\n... (共 {len(result)} 条，已截断)"
            output_payloads.append(MarkdownPayload(content=text))
            ctx["output_kinds"].append("markdown")
            data_field = result if include_data else None

    elif isinstance(result, dict):
        # 判断是否需要 table 单行
        if "table" in display_types and force_single_row_table_for_dict:
            row = {k: result[k] for k in result}
            table_payload, stats = _build_table_payload(
                [row],
                title=table_title or func.__name__,
                columns=table_columns,
                max_rows=1,
            )
            output_payloads.append(table_payload)
            ctx.update(stats)
            ctx["output_kinds"].append("table")
            if "markdown" in display_types:
                kv_preview = ", ".join(f"{k}={str(v)[:20]}" for k, v in list(result.items())[:10])
                output_payloads.append(MarkdownPayload(content=f"{table_payload.title} 字典预览: {kv_preview}"))
                ctx["output_kinds"].append("markdown")
        else:
            if "markdown" in display_types or not display_types:
                kv_preview = "\n".join(f"- {k}: {repr(v)[:120]}" for k, v in list(result.items())[:30])
                output_payloads.append(MarkdownPayload(content=f"字典内容:\n{kv_preview}"))
                ctx["output_kinds"].append("markdown")
        data_field = result if include_data else None

    else:
        # 其他类型 -> 转成字符串 markdown
        text = repr(result)
        output_payloads.append(MarkdownPayload(content=text))
        ctx["output_kinds"].append("markdown")
        data_field = result if include_raw_data else None

    # 3. 生成摘要 model_text
    model_text = summarizer(result, ctx) if summarizer else default_summarizer(result, ctx)
    if model_text and len(model_text) > max_model_text_chars:
        model_text = model_text[: max_model_text_chars - 20] + "...(截断)"

    # 4. metadata
    metadata = {
        "function": func.__name__,
        "execution_ms": round(elapsed_ms, 2),
        "original_type": original_type,
    }
    if "row_count" in ctx:
        metadata["row_count"] = ctx["row_count"]
        metadata["truncated"] = ctx["truncated"]
        metadata["columns"] = ctx["columns"]
    if metadata_extra:
        try:
            extra = metadata_extra(result, ctx) or {}
            metadata.update(extra)
        except Exception as e:
            metadata["metadata_extra_error"] = str(e)

    # 5. 组装 ToolResult
    tool_result = ToolResult(
        model_text=model_text,
        display=output_payloads,
        data=data_field,
        metadata=metadata,
    )
    return tool_result.model_dump()


# ---------------------------
# 额外：一个可选的快捷封装帮助直接创建 fastmcp Tool (如果需要)
# ---------------------------
def fastmcp_tool(
    *tool_args,
    wrapper_kwargs: dict | None = None,
    **tool_kwargs,
):
    """
    可选：结合 fastmcp.tools.tool 装饰器使用。
    使用方式：
        from fastmcp.tools import tool as mcp_tool
        from tool_wrapper import fastmcp_tool

        @fastmcp_tool(name="list_users", wrapper_kwargs={"display":"table"})
        def list_users():
            return [{"id":1,"name":"Alice"}]

    说明：
        - 需要 fastmcp 已安装
        - wrapper_kwargs 传给上面的 tool() 装饰器
        - tool_args / tool_kwargs 透传给 fastmcp.tools.tool
    """
    try:
        from fastmcp.tools import tool as mcp_tool  # 延迟导入
    except ImportError as e:
        raise RuntimeError("fastmcp 未安装，无法使用 fastmcp_tool 包装") from e

    wrapper_kwargs = wrapper_kwargs or {}

    def outer(fn):
        decorated = tool(**wrapper_kwargs)(fn)
        return mcp_tool(*tool_args, **tool_kwargs)(decorated)

    return outer
