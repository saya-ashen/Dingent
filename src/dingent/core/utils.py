from __future__ import annotations

import re
from pathlib import Path


def to_camel(string: str) -> str:
    """snake_case → camelCase"""
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


def normalize_agent_name(name: str) -> str:
    """确保 Agent 名称在整个系统中一致的规范化逻辑"""
    return re.sub(r"\W|^(?=\d)", "_", name)
