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
    "assistant-message",
    "assistant-message-complete",
    "assistant_turn_complete",
    "turn_complete",
}

# 定义常见的模型角色字段值
ASSISTANT_ROLES = {"assistant", "model", "bot", "claude", "codex"}

# 常见结束原因字段
FINISH_REASONS = {"stop", "end", "complete", "completed", "done"}


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

    # 直接布尔标志
    for key in ("is_last_turn", "conversation_end", "conversation_finished", "final", "closed"):
        if key in event and bool(event.get(key)):
            return True

    # 事件类型语义：模型完成一轮输出
    event_type = (event.get("type") or event.get("event") or "").replace("_", "-").lower()
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
            nested_type = (sub.get("type") or sub.get("event") or "").replace("_", "-").lower()
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

    # 角色视角：模型端完成一轮输出
    role = (event.get("role") or event.get("speaker") or event.get("who") or "").lower()
    if role in ASSISTANT_ROLES and not bool(event.get("partial")):
        # 有实质输出才认为一轮结束
        if any(event.get(key) for key in ("text", "display", "message", "content")):
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
