"""
通知器基类

定义通知器的通用接口
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional
from ..models import NotificationConfig, NotificationLevel


class BaseNotifier(ABC):
    """通知器基类"""

    def __init__(self, config: NotificationConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def notify(self, title: str, message: str, level: NotificationLevel = NotificationLevel.INFO, **kwargs):
        """发送通知"""
        pass

    def is_enabled(self) -> bool:
        """检查是否启用"""
        return True

    def log_notification(self, title: str, message: str, level: NotificationLevel):
        """记录通知日志"""
        self.logger.debug(f"发送通知: {title} - {message} (级别: {level.value})")