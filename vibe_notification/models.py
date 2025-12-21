"""
数据模型模块

包含所有数据类、枚举和类型定义
"""

from enum import Enum
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


class NotificationLevel(Enum):
    """通知级别"""
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"

    def __str__(self) -> str:
        """返回枚举值，便于日志与比较"""
        return self.value


class PlatformType(Enum):
    """平台类型"""
    MACOS = "darwin"
    LINUX = "linux"
    WINDOWS = "windows"
    UNKNOWN = "unknown"


@dataclass
class NotificationConfig:
    """通知配置"""
    enable_sound: bool = True
    enable_notification: bool = True
    notification_timeout: int = 10000  # 毫秒
    sound_type: str = "Glass"  # 默认声音改为 Glass
    sound_volume: float = 0.1  # 音量 0.0-1.0，默认 10%
    log_level: str = "INFO"
    detect_conversation_end: bool = True
    language: str = "zh"  # 语言：zh 或 en

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotificationConfig":
        """从字典创建"""
        return cls(**data)


@dataclass
class NotificationEvent:
    """通知事件"""
    type: str
    agent: str
    message: str
    summary: str
    timestamp: str
    is_last_turn: bool = False
    tool_name: Optional[str] = None
    conversation_end: bool = False
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotificationEvent":
        """从字典创建"""
        return cls(**data)
