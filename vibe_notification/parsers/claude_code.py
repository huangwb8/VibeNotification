"""
Claude Code 解析器

解析 Claude Code 钩子事件
"""

import json
import os
import sys
import select
from datetime import datetime
from typing import Any, Dict
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
        # 检查 stdin 是否有数据
        if not sys.stdin.isatty() and self._stdin_has_data():
            return True

        # 检查环境变量
        if os.environ.get("CLAUDE_HOOK_COMMAND") or os.environ.get("CLAUDE_HOOK_TOOL_NAME"):
            return True

        return False

    def parse(self) -> NotificationEvent:
        """解析 Claude Code 钩子事件"""
        try:
            if not sys.stdin.isatty():
                hook_input = sys.stdin.read()
                if hook_input:
                    hook_data = json.loads(hook_input)
                    tool_name = hook_data.get("toolName", "unknown")

                    # 检测是否是会话结束
                    conversation_end = detect_conversation_end_from_hook(hook_data)

                    event = NotificationEvent(
                        type="agent-turn-complete",
                        agent="claude-code",
                        message=f"使用工具: {tool_name}",
                        summary=f"Claude Code 完成了 {tool_name} 操作",
                        timestamp=datetime.now().isoformat(),
                        tool_name=tool_name,
                        conversation_end=conversation_end,
                        is_last_turn=conversation_end,
                        metadata=hook_data
                    )
                    return event
        except Exception as e:
            self.logger.error(f"解析 Claude Code 事件失败: {e}")

        # 回退事件
        return self.create_fallback_event("claude-code", "Claude Code 操作完成")
