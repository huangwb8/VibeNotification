"""
会话结束检测器

检测会话是否结束
"""

from typing import Any, Dict

# 定义常见的“本轮完成”事件类型关键字
TURN_COMPLETE_TYPES = {
    "agent-turn-complete",
    "turn-complete",
    "assistant-turn-complete",
    "assistant-message-complete",
    "assistant_turn_complete",
    "turn_complete",
}

# 常见结束原因字段
FINISH_REASONS = {"stop", "end", "complete", "completed", "done"}

CODEX_NOTIFY_EVENT_TYPES = {
    "agent-turn-complete",
    "turn-completed",
    "session-end",
}

CODEX_APP_SERVER_METHODS = {"turn/completed"}

CODEX_HOOK_EVENT_NAMES = {"sessionstart", "userpromptsubmit", "stop"}


def _normalize_event_name(value: Any) -> str:
    """标准化事件名，统一比较格式。"""
    if not isinstance(value, str):
        return ""
    return value.replace("_", "-").strip().lower()


def _looks_like_codex_payload(event: Dict[str, Any]) -> bool:
    """判断事件是否像 Codex CLI / hook / app-server 负载。"""
    codex_keys = {
        "thread-id", "thread_id",
        "turn-id", "turn_id",
        "input-messages", "input_messages",
        "last-assistant-message", "last_assistant_message",
        "hook_event_name", "session_id", "permission_mode",
        "stop_hook_active", "client",
    }

    if any(key in event for key in codex_keys):
        return True

    event_type = _normalize_event_name(event.get("type") or event.get("event"))
    if event_type in CODEX_NOTIFY_EVENT_TYPES:
        return True

    method = _normalize_event_name(event.get("method"))
    if method in CODEX_APP_SERVER_METHODS:
        return True

    for key in ("agent", "client"):
        value = event.get(key)
        if isinstance(value, str) and "codex" in value.lower():
            return True

    return False


def _detect_codex_conversation_end(event: Dict[str, Any]) -> bool:
    """基于 Codex 官方事件形状判断是否为真实 turn 结束。"""
    for key in ("is_last_turn", "conversation_end", "conversation_finished", "final", "closed"):
        if key in event and bool(event.get(key)):
            return True

    hook_event_name = event.get("hook_event_name")
    if isinstance(hook_event_name, str) and hook_event_name.strip().lower() in CODEX_HOOK_EVENT_NAMES:
        return False

    event_type = _normalize_event_name(event.get("type") or event.get("event"))
    if event_type in CODEX_NOTIFY_EVENT_TYPES:
        return True

    method = _normalize_event_name(event.get("method"))
    if method in CODEX_APP_SERVER_METHODS:
        return True

    for container_key in ("payload", "metadata", "data", "details"):
        sub = event.get(container_key)
        if not isinstance(sub, dict):
            continue

        nested_type = _normalize_event_name(sub.get("type") or sub.get("event"))
        if nested_type in CODEX_NOTIFY_EVENT_TYPES:
            return True

        nested_method = _normalize_event_name(sub.get("method"))
        if nested_method in CODEX_APP_SERVER_METHODS:
            return True

    return False


def detect_conversation_end_from_hook(hook_data: Dict[str, Any]) -> bool:
    """从钩子数据检测会话结束"""
    # 复用通用检测逻辑
    if detect_conversation_end(hook_data):
        return True

    tool_name = hook_data.get("toolName", "") or hook_data.get("tool_name", "")

    # Claude/Codex 钩子是在模型完成一轮输出后触发的，默认视为该轮对话结束
    if tool_name:
        return True

    return False


def detect_conversation_end(event: Dict[str, Any]) -> bool:
    """检测会话是否结束"""
    if not isinstance(event, dict):
        return False

    if _looks_like_codex_payload(event):
        return _detect_codex_conversation_end(event)

    # 直接布尔标志
    for key in ("is_last_turn", "conversation_end", "conversation_finished", "final", "closed"):
        if key in event and bool(event.get(key)):
            return True

    # 事件类型语义：模型完成一轮输出
    event_type = _normalize_event_name(event.get("type") or event.get("event"))
    if event_type:
        if event_type in TURN_COMPLETE_TYPES or ("turn" in event_type and "complete" in event_type):
            return True

    # 结束/停止原因
    for key in ("finish_reason", "stop_reason", "stopReason", "reason"):
        reason = event.get(key)
        if isinstance(reason, str) and reason.lower() in FINISH_REASONS:
            return True

    # 检查嵌套字典
    for container_key in ("payload", "metadata", "data", "details"):
        sub = event.get(container_key)
        if isinstance(sub, dict):
            # 嵌套布尔标志
            for key in ("conversation_end", "conversation_finished", "is_last_turn", "final"):
                if key in sub and bool(sub.get(key)):
                    return True
            # 嵌套事件类型
            nested_type = _normalize_event_name(sub.get("type") or sub.get("event"))
            if nested_type:
                if nested_type in TURN_COMPLETE_TYPES or ("turn" in nested_type and "complete" in nested_type):
                    return True
            for key in ("finish_reason", "stop_reason", "reason"):
                reason = sub.get(key)
                if isinstance(reason, str) and reason.lower() in FINISH_REASONS:
                    return True

    # 状态字符串
    state = event.get("conversation_state") or event.get("state")
    if isinstance(state, str):
        if state.lower() in ("finished", "ended", "closed", "complete"):
            return True

    # turn/total 启发式
    try:
        turn = event.get("turn")
        total = event.get("total_turns") or event.get("turns_total") or event.get("total_turns_estimate")
        if isinstance(turn, int) and isinstance(total, int) and turn >= total:
            return True
    except Exception:
        pass

    return False
