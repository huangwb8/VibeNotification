"""
解析器模块

包含各种事件解析器的实现
"""

from .base import BaseParser
from .claude_code import ClaudeCodeParser
from .codex import CodexParser
from ._stdin import get_stdin_json
from .routing import detect_parser_type, is_claude_context, is_codex_context

__all__ = [
    "BaseParser",
    "ClaudeCodeParser",
    "CodexParser",
    "get_stdin_json",
    "detect_parser_type",
    "is_claude_context",
    "is_codex_context",
]
