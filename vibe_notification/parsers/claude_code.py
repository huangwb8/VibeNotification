"""
Claude Code 解析器

解析 Claude Code 钩子事件。
支持两种来源：
1. 环境变量 CLAUDE_HOOK_EVENT（旧版 / 部分场景）
2. stdin JSON 中的 hook_event_name 字段（Claude Code 官方 Stop 钩子）
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from .base import BaseParser
from ._stdin import get_stdin_json
from ..models import NotificationEvent


class ClaudeCodeParser(BaseParser):
    """Claude Code 解析器"""

    # Claude Code 钩子事件名（与 Claude Code 发送的大小写一致）
    HOOK_EVENTS = {"Stop", "SessionEnd", "SubagentStop", "PostToolUse", "PreToolUse", "ToolError"}

    def _get_hook_event(self) -> Optional[str]:
        """从环境变量或 stdin JSON 获取钩子事件名。"""
        # 优先检查环境变量
        env_event = os.environ.get("CLAUDE_HOOK_EVENT")
        if env_event:
            return env_event

        # 从 stdin JSON 检查 hook_event_name
        stdin_json = get_stdin_json()
        if isinstance(stdin_json, dict):
            name = stdin_json.get("hook_event_name")
            if name and name in self.HOOK_EVENTS:
                return name

        return None

    def can_parse(self) -> bool:
        """检查是否在 Claude Code 钩子上下文中。"""
        # 1. 通过环境变量或 stdin hook_event_name 匹配
        if self._get_hook_event():
            return True

        # 2. stdin 有 JSON 数据（用于 stdin 直接传入工具数据的场景）
        if get_stdin_json():
            return True

        # 3. 其他 Claude Code 相关环境变量
        if os.environ.get("CLAUDE_HOOK_COMMAND") or os.environ.get("CLAUDE_HOOK_TOOL_NAME"):
            return True

        return False

    def _parse_hook_event(self) -> Optional[NotificationEvent]:
        """解析钩子事件（环境变量 + stdin JSON 统一入口）。"""
        hook_event = self._get_hook_event()
        stdin_json = get_stdin_json()

        if hook_event == "Stop":
            return NotificationEvent(
                type="agent-turn-complete",
                agent="claude-code",
                message="Claude 回复完成",
                summary="Claude Code 已完成回复",
                timestamp=datetime.now().isoformat(),
                conversation_end=True,
                is_last_turn=True,
                metadata={"event": "Stop", "source": "hook", "stdin": stdin_json or {}}
            )

        if hook_event == "SubagentStop":
            return NotificationEvent(
                type="agent-turn-complete",
                agent="claude-code-subagent",
                message="子代理完成任务",
                summary="Claude Code 子代理已完成",
                timestamp=datetime.now().isoformat(),
                conversation_end=True,
                is_last_turn=True,
                metadata={"event": "SubagentStop", "source": "hook", "stdin": stdin_json or {}}
            )

        if hook_event == "SessionEnd":
            return NotificationEvent(
                type="session-end",
                agent="claude-code",
                message="Claude 会话结束",
                summary="Claude Code 会话已结束",
                timestamp=datetime.now().isoformat(),
                conversation_end=True,
                is_last_turn=True,
                metadata={"event": "SessionEnd", "source": "hook", "stdin": stdin_json or {}}
            )

        if hook_event == "PostToolUse":
            tool_name = os.environ.get("CLAUDE_HOOK_TOOL_NAME", "unknown")
            return NotificationEvent(
                type="tool-complete",
                agent="claude-code",
                message=f"工具调用完成: {tool_name}",
                summary=f"已完成 {tool_name} 工具调用",
                timestamp=datetime.now().isoformat(),
                tool_name=tool_name,
                conversation_end=False,
                is_last_turn=False,
                metadata={"event": "PostToolUse", "source": "hook", "tool_name": tool_name}
            )

        if hook_event == "PreToolUse":
            self.logger.debug("工具调用开始，跳过通知: %s", os.environ.get("CLAUDE_HOOK_TOOL_NAME", "unknown"))
            return None

        if hook_event == "ToolError":
            tool_name = os.environ.get("CLAUDE_HOOK_TOOL_NAME", "unknown")
            return NotificationEvent(
                type="tool-error",
                agent="claude-code",
                message=f"工具调用失败: {tool_name}",
                summary=f"{tool_name} 工具调用出现错误",
                timestamp=datetime.now().isoformat(),
                tool_name=tool_name,
                conversation_end=False,
                is_last_turn=False,
                metadata={"event": "ToolError", "source": "hook", "tool_name": tool_name}
            )

        return None

    def _parse_stdin_data(self) -> Optional[NotificationEvent]:
        """解析 stdin JSON 数据（非 hook_event_name 场景的回退）。"""
        from ..detectors.conversation import detect_conversation_end_from_hook

        stdin_json = get_stdin_json()
        if not isinstance(stdin_json, dict):
            return None

        # 如果已经有 hook_event_name 匹配，跳过（已在 _parse_hook_event 处理）
        if stdin_json.get("hook_event_name") in self.HOOK_EVENTS:
            return None

        tool_name = stdin_json.get("toolName") or stdin_json.get("tool_name")
        conversation_end = detect_conversation_end_from_hook(stdin_json)

        if tool_name:
            message = f"使用工具: {tool_name}"
            summary = f"Claude Code 完成了 {tool_name} 操作"
            event_type = "tool-complete"
        else:
            message = stdin_json.get("message") or "Claude Code 操作完成"
            summary = stdin_json.get("summary") or message
            event_type = "agent-turn-complete" if conversation_end else "operation-complete"

        return NotificationEvent(
            type=event_type,
            agent="claude-code",
            message=message,
            summary=summary,
            timestamp=datetime.now().isoformat(),
            tool_name=tool_name,
            conversation_end=conversation_end,
            is_last_turn=conversation_end,
            metadata={"source": "stdin", "data": stdin_json}
        )

    def parse(self) -> Optional[NotificationEvent]:
        """解析 Claude Code 钩子事件。"""
        # 首先处理钩子事件（环境变量或 stdin hook_event_name）
        event = self._parse_hook_event()
        if event is not None:
            return event

        # 回退到 stdin 数据解析
        event = self._parse_stdin_data()
        if event is not None:
            return event

        # 有钩子上下文但没有具体事件类型，创建回退事件
        if os.environ.get("CLAUDE_HOOK_COMMAND") or os.environ.get("CLAUDE_HOOK_TOOL_NAME"):
            return self.create_fallback_event("claude-code", "Claude Code 操作完成")

        return None
