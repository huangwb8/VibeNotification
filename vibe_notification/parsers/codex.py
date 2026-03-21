"""
Codex 解析器

解析 Codex 事件
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from .base import BaseParser
from ..models import NotificationEvent
from ..detectors.conversation import detect_conversation_end


class CodexParser(BaseParser):
    """Codex 解析器"""

    CODEX_HOOK_EVENT_TYPES = {
        "sessionstart": "session-start",
        "userpromptsubmit": "user-prompt-submit",
        "stop": "stop-hook",
    }

    def _load_event_data(self) -> Optional[Dict[str, Any]]:
        """读取并校验最后一个 argv JSON。"""
        if len(sys.argv) < 2:
            return None

        try:
            event_data = json.loads(sys.argv[-1])
        except Exception:
            return None

        if not isinstance(event_data, dict):
            return None

        return event_data

    def _get_value(self, event_data: Dict[str, Any], *keys: str) -> Any:
        """兼容 kebab-case / snake_case 的字段读取。"""
        for key in keys:
            if key in event_data:
                return event_data.get(key)
        return None

    def _normalize_hook_event_name(self, event_data: Dict[str, Any]) -> str:
        """标准化 hook 事件名。"""
        value = self._get_value(event_data, "hook_event_name")
        if not isinstance(value, str):
            return ""
        return value.strip().lower()

    def _infer_event_type(self, event_data: Dict[str, Any]) -> str:
        """推断事件类型。"""
        hook_event_name = self._normalize_hook_event_name(event_data)
        if hook_event_name in self.CODEX_HOOK_EVENT_TYPES:
            return self.CODEX_HOOK_EVENT_TYPES[hook_event_name]

        method = self._get_value(event_data, "method")
        if isinstance(method, str) and method.strip():
            return method

        event_type = self._get_value(event_data, "type", "event")
        if isinstance(event_type, str) and event_type.strip():
            return event_type

        return "unknown"

    def _infer_agent(self, event_data: Dict[str, Any]) -> str:
        """推断代理名称。"""
        agent = self._get_value(event_data, "agent")
        if isinstance(agent, str) and agent.strip():
            return agent

        hook_event_name = self._normalize_hook_event_name(event_data)
        if hook_event_name:
            return "codex-hook"

        client = self._get_value(event_data, "client")
        if isinstance(client, str) and client.strip():
            return "codex"

        return "codex"

    def _infer_message(self, event_data: Dict[str, Any], conversation_end: bool) -> str:
        """推断通知消息。"""
        assistant_message = self._get_value(
            event_data,
            "last_assistant_message",
            "last-assistant-message",
            "message",
        )
        if isinstance(assistant_message, str) and assistant_message.strip():
            return assistant_message

        hook_event_name = self._normalize_hook_event_name(event_data)
        if hook_event_name == "userpromptsubmit":
            return "Codex 已接收用户指令"
        if hook_event_name == "sessionstart":
            return "Codex 会话已启动"
        if hook_event_name == "stop":
            return "Codex Stop hook 已触发"

        if conversation_end:
            return "Codex 回复完成"

        return "Codex 事件已接收"

    def can_parse(self) -> bool:
        """检查是否可以解析 Codex 事件"""
        # Codex notify / hooks 都会将 JSON 作为最后一个参数传入
        return self._load_event_data() is not None

    def parse(self) -> Optional[NotificationEvent]:
        """解析 Codex 事件"""
        try:
            event_data = self._load_event_data()
            if event_data is None:
                return None

            conversation_end = detect_conversation_end(event_data)
            agent = self._infer_agent(event_data)
            event_type = self._infer_event_type(event_data)
            message = self._infer_message(event_data, conversation_end)
            summary = message if conversation_end else f"{message}（忽略通知）"

            event = NotificationEvent(
                type=event_type,
                agent=agent,
                message=message,
                summary=summary,
                timestamp=event_data.get("timestamp", datetime.now().isoformat()),
                tool_name=self._get_value(event_data, "tool_name", "toolName"),
                conversation_end=conversation_end,
                is_last_turn=conversation_end,
                metadata=event_data
            )
            return event
        except Exception as e:
            self.logger.error(f"解析 Codex 事件失败: {e}")

        # 回退事件
        return self.create_fallback_event("codex", "Codex 操作完成")
