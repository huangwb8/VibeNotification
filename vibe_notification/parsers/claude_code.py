"""
Claude Code 解析器

解析 Claude Code 钩子事件
"""

import json
import os
import sys
import select
from datetime import datetime
from typing import Any, Dict, Optional
from .base import BaseParser
from ..models import NotificationEvent
from ..detectors.conversation import detect_conversation_end_from_hook


class ClaudeCodeParser(BaseParser):
    """Claude Code 解析器"""

    def _stdin_has_data(self) -> bool:
        """检查 stdin 是否有可读数据"""
        try:
            readable, _, _ = select.select([sys.stdin], [], [], 0)
            return bool(readable)
        except Exception:
            return False

    def can_parse(self) -> bool:
        """检查是否在 Claude Code 钩子上下文中"""
        # 检查钩子事件环境变量
        hook_event = os.environ.get("CLAUDE_HOOK_EVENT")
        if hook_event in (
            "SessionEnd", "Stop", "SubagentStop",
            "PostToolUse", "PreToolUse", "ToolError"
        ):
            return True

        # 检查 stdin 是否有数据（用于某些钩子事件的额外数据）
        if not sys.stdin.isatty() and self._stdin_has_data():
            return True

        # 检查其他环境变量
        if os.environ.get("CLAUDE_HOOK_COMMAND") or os.environ.get("CLAUDE_HOOK_TOOL_NAME"):
            return True

        return False

    def _parse_hook_event(self) -> Optional[NotificationEvent]:
        """解析基于环境变量的钩子事件"""
        hook_event = os.environ.get("CLAUDE_HOOK_EVENT")

        # Stop 事件 - Claude 完成一次完整回复
        if hook_event == "Stop":
            # Stop 事件通常表示一次完整的回复结束，应该触发通知
            return NotificationEvent(
                type="agent-turn-complete",
                agent="claude-code",
                message="Claude 回复完成",
                summary="Claude Code 已完成回复",
                timestamp=datetime.now().isoformat(),
                conversation_end=True,  # Stop 事件表示回复完成，应该触发会话结束通知
                is_last_turn=True,
                metadata={"event": "Stop", "source": "hook"}
            )

        # SubagentStop 事件 - 子代理完成任务
        if hook_event == "SubagentStop":
            return NotificationEvent(
                type="agent-turn-complete",
                agent="claude-code-subagent",
                message="子代理完成任务",
                summary="Claude Code 子代理已完成",
                timestamp=datetime.now().isoformat(),
                conversation_end=True,  # 子代理完成也表示一次任务完成
                is_last_turn=True,
                metadata={"event": "SubagentStop", "source": "hook"}
            )

        # SessionEnd 事件 - 会话结束
        if hook_event == "SessionEnd":
            return NotificationEvent(
                type="session-end",
                agent="claude-code",
                message="Claude 会话结束",
                summary="Claude Code 会话已结束",
                timestamp=datetime.now().isoformat(),
                conversation_end=True,
                is_last_turn=True,
                metadata={"event": "SessionEnd", "source": "hook"}
            )

        # PostToolUse 事件 - 工具调用完成后
        if hook_event == "PostToolUse":
            # 尝试从环境变量获取工具信息
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

        # PreToolUse 事件 - 工具调用前（通常不需要通知）
        if hook_event == "PreToolUse":
            # 工具开始时不发送通知，避免干扰
            self.logger.debug(f"工具调用开始，跳过通知: {os.environ.get('CLAUDE_HOOK_TOOL_NAME', 'unknown')}")
            return None

        # ToolError 事件 - 工具调用出错
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
        """解析 stdin 数据（用于某些钩子的额外信息）"""
        try:
            if not sys.stdin.isatty() and self._stdin_has_data():
                hook_input = sys.stdin.read()
                if hook_input:
                    hook_data = json.loads(hook_input)

                    tool_name = hook_data.get("toolName") or hook_data.get("tool_name")
                    conversation_end = detect_conversation_end_from_hook(hook_data)

                    # 根据数据类型处理
                    if tool_name:
                        message = f"使用工具: {tool_name}"
                        summary = f"Claude Code 完成了 {tool_name} 操作"
                        event_type = "tool-complete"
                    else:
                        message = hook_data.get("message") or "Claude Code 操作完成"
                        summary = hook_data.get("summary") or message
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
                        metadata={"source": "stdin", "data": hook_data}
                    )

        except json.JSONDecodeError as e:
            self.logger.error(f"解析 stdin JSON 数据失败: {e}")
        except Exception as e:
            self.logger.error(f"处理 stdin 数据时出错: {e}")

        return None

    def parse(self) -> Optional[NotificationEvent]:
        """解析 Claude Code 钩子事件"""
        # 首先处理基于环境变量的钩子事件
        event = self._parse_hook_event()
        if event is not None:
            return event

        # 如果没有钩子事件，尝试解析 stdin 数据
        event = self._parse_stdin_data()
        if event is not None:
            return event

        # 如果都没有，检查是否是其他类型的钩子上下文
        if (os.environ.get("CLAUDE_HOOK_COMMAND") or
            os.environ.get("CLAUDE_HOOK_TOOL_NAME")):
            # 有钩子上下文但没有具体事件类型，创建回退事件
            return self.create_fallback_event("claude-code", "Claude Code 操作完成")

        # 完全没有相关上下文
        return None
