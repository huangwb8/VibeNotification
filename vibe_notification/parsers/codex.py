"""
Codex 解析器

解析 Codex 事件
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict
from .base import BaseParser
from ..models import NotificationEvent
from ..detectors.conversation import detect_conversation_end


class CodexParser(BaseParser):
    """Codex 解析器"""

    def can_parse(self) -> bool:
        """检查是否可以解析 Codex 事件"""
        # 检查是否有命令行参数
        return len(sys.argv) == 2

    def parse(self) -> NotificationEvent:
        """解析 Codex 事件"""
        try:
            event_json = sys.argv[1]
            event_data = json.loads(event_json)

            # 检测会话结束
            conversation_end = detect_conversation_end(event_data)

            event = NotificationEvent(
                type=event_data.get("type", "unknown"),
                agent=event_data.get("agent", "unknown"),
                message=event_data.get("message", ""),
                summary=event_data.get("summary", ""),
                timestamp=event_data.get("timestamp", datetime.now().isoformat()),
                tool_name=event_data.get("tool_name"),
                conversation_end=conversation_end,
                is_last_turn=conversation_end,
                metadata=event_data
            )
            return event
        except Exception as e:
            self.logger.error(f"解析 Codex 事件失败: {e}")

        # 回退事件
        return self.create_fallback_event("codex", "Codex 操作完成")