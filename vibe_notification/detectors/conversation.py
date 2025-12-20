"""
会话结束检测器

检测会话是否结束
"""

from typing import Any, Dict


def detect_conversation_end_from_hook(hook_data: Dict[str, Any]) -> bool:
    """从钩子数据检测会话结束"""
    # 这里可以添加更智能的检测逻辑
    # 例如：检测特定的工具序列或模式
    tool_name = hook_data.get("toolName", "")

    # 如果使用了某些特定的"结束"工具
    end_tools = ["ExitPlanMode", "Skill", "Task"]
    if tool_name in end_tools:
        return True

    # 检查是否有结束标志
    if hook_data.get("conversation_end") or hook_data.get("is_last_turn"):
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

    # 检查嵌套字典
    for container_key in ("payload", "metadata", "data", "details"):
        sub = event.get(container_key)
        if isinstance(sub, dict):
            for key in ("conversation_end", "conversation_finished", "is_last_turn", "final"):
                if key in sub and bool(sub.get(key)):
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