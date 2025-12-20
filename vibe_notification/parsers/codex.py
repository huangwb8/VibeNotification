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

    def can_parse(self) -> bool:
        """检查是否可以解析 Codex 事件"""
        # Codex notify 会将事件 JSON 作为“最后一个参数”传入，可能伴随 `-m vibe_notification`
        # 等额外参数；因此只要末尾参数是合法 JSON 就认为可解析
        if len(sys.argv) < 2:
            return False
        try:
            json.loads(sys.argv[-1])
            return True
        except Exception:
            return False

    def parse(self) -> Optional[NotificationEvent]:
        """解析 Codex 事件"""
        try:
            # 兼容 `python -m vibe_notification <JSON>` 或 `notify=["python","-m","vibe_notification"]`
            # 等形式，取最后一个参数作为事件 JSON
            event_json = sys.argv[-1]
            event_data = json.loads(event_json)

            # 检测会话结束
            conversation_end = detect_conversation_end(event_data)
            agent = event_data.get("agent") or "codex"

            event = NotificationEvent(
                type=event_data.get("type", "unknown"),
                agent=agent,
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
