"""
解析器基类

定义事件解析器的通用接口
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from ..models import NotificationEvent


class BaseParser(ABC):
    """解析器基类"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def can_parse(self) -> bool:
        """检查是否可以解析当前上下文"""
        pass

    @abstractmethod
    def parse(self) -> Optional[NotificationEvent]:
        """解析事件，返回 None 表示不发送通知"""
        pass

    def create_fallback_event(self, agent: str = "unknown", message: str = "未知事件") -> NotificationEvent:
        """创建回退事件"""
        from datetime import datetime
        return NotificationEvent(
            type="unknown",
            agent=agent,
            message=message,
            summary=message,
            timestamp=datetime.now().isoformat(),
            conversation_end=False,
            is_last_turn=False
        )
