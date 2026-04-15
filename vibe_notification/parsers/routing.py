"""
解析路由模块

负责在进入具体 parser 之前判定当前事件属于 Claude Code 还是 Codex。
这里仅做来源识别，不承载任何具体的业务解析逻辑。
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Mapping, Optional, Sequence

from ._stdin import get_stdin_json

CLAUDE_HOOK_EVENTS = {"stop", "sessionend", "subagentstop", "posttooluse", "pretooluse", "toolerror"}
CODEX_HOOK_EVENTS = {"sessionstart", "userpromptsubmit", "pretooluse", "posttooluse", "stop"}
CODEX_NOTIFY_EVENT_TYPES = {"agent-turn-complete", "turn-completed", "session-end"}
CODEX_APP_SERVER_METHODS = {"turn/completed"}


def _normalize_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.replace("_", "-").strip().lower()


def get_argv_json(argv: Optional[Sequence[str]] = None) -> Optional[Dict[str, Any]]:
    """尝试从 argv 最后一个参数读取 JSON 事件。"""
    values = list(sys.argv if argv is None else argv)
    if len(values) < 2:
        return None

    try:
        parsed = json.loads(values[-1])
    except Exception:
        return None

    return parsed if isinstance(parsed, dict) else None


def is_codex_payload(payload: Optional[Dict[str, Any]]) -> bool:
    """判断负载是否属于 Codex。"""
    if not isinstance(payload, dict):
        return False

    hook_event_name = _normalize_name(payload.get("hook_event_name") or payload.get("hookEventName"))
    event_type = _normalize_name(payload.get("type") or payload.get("event"))
    method = _normalize_name(payload.get("method"))

    if method in CODEX_APP_SERVER_METHODS:
        return True

    if event_type in CODEX_NOTIFY_EVENT_TYPES:
        return True

    for key in ("thread-id", "thread_id", "turn-id", "turn_id", "input-messages", "input_messages"):
        if key in payload:
            return True

    for key in ("client", "agent", "model"):
        value = payload.get(key)
        if isinstance(value, str) and "codex" in value.lower():
            return True

    if hook_event_name in CODEX_HOOK_EVENTS - {"stop"}:
        return True

    if hook_event_name == "stop":
        for key in ("client", "agent", "model"):
            value = payload.get(key)
            if isinstance(value, str) and "codex" in value.lower():
                return True

        for key in ("thread-id", "thread_id", "turn-id", "turn_id", "input-messages", "input_messages"):
            if key in payload:
                return True

    return False


def is_claude_payload(payload: Optional[Dict[str, Any]]) -> bool:
    """判断负载是否属于 Claude Code。"""
    if not isinstance(payload, dict):
        return False

    if is_codex_payload(payload):
        return False

    hook_event_name = _normalize_name(payload.get("hook_event_name") or payload.get("hookEventName"))
    if hook_event_name in CLAUDE_HOOK_EVENTS:
        return True

    tool_name = payload.get("toolName") or payload.get("tool_name")
    if isinstance(tool_name, str) and tool_name.strip():
        return True

    generic_keys = {
        "finish_reason",
        "stop_reason",
        "stopReason",
        "reason",
        "conversation_end",
        "conversation_finished",
        "final",
        "closed",
        "message",
        "summary",
    }
    return any(key in payload for key in generic_keys)


def detect_parser_type(
    argv: Optional[Sequence[str]] = None,
    stdin_json: Optional[Dict[str, Any]] = None,
    environ: Optional[Mapping[str, str]] = None,
) -> Optional[str]:
    """检测当前上下文应使用的 parser 类型。"""
    env = os.environ if environ is None else environ

    if env.get("CLAUDE_HOOK_EVENT") or env.get("CLAUDE_HOOK_COMMAND") or env.get("CLAUDE_HOOK_TOOL_NAME"):
        return "claude_code"

    argv_json = get_argv_json(argv)
    if is_codex_payload(argv_json):
        return "codex"
    if is_claude_payload(argv_json):
        return "claude_code"

    payload = get_stdin_json() if stdin_json is None else stdin_json
    if is_codex_payload(payload):
        return "codex"
    if is_claude_payload(payload):
        return "claude_code"

    return None


def is_codex_context() -> bool:
    return detect_parser_type() == "codex"


def is_claude_context() -> bool:
    return detect_parser_type() == "claude_code"
