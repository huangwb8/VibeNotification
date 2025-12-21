"""
VibeNotification - 为 Claude Code 和 Codex 提供智能会话结束通知

主要功能：
1. 检测 Claude Code 和 Codex 的会话结束事件
2. 跨平台系统通知（macOS、Linux、Windows）
3. 智能声音提示
4. 可配置的通知行为
5. 详细的日志记录
"""

__version__ = "1.0.1"
__author__ = "Bensz Conan"
__email__ = "35643122+huangwb8@users.noreply.github.com"

# 主要导出
from .core import VibeNotifier
from .models import NotificationConfig, NotificationEvent, NotificationLevel, PlatformType
from .config import load_config, save_config
from .cli import main

# 新增的组件导出
from .managers import ParserManager, NotifierManager, NotificationBuilder
from .factories import ParserFactory, NotifierFactory, AdapterFactory
from .adapters import PlatformAdapter, CommandExecutor, DefaultCommandExecutor, ProcessResult
from .exceptions import (
    VibeNotificationError,
    ConfigurationError,
    ParserError,
    NotifierError,
    CommandExecutionError,
    UnsupportedPlatformError
)

__all__ = [
    # 核心组件
    "VibeNotifier",

    # 数据模型
    "NotificationConfig",
    "NotificationEvent",
    "NotificationLevel",
    "PlatformType",

    # 配置
    "load_config",
    "save_config",

    # CLI
    "main",

    # 管理器
    "ParserManager",
    "NotifierManager",
    "NotificationBuilder",

    # 工厂
    "ParserFactory",
    "NotifierFactory",
    "AdapterFactory",

    # 适配器
    "PlatformAdapter",
    "CommandExecutor",
    "DefaultCommandExecutor",
    "ProcessResult",

    # 异常
    "VibeNotificationError",
    "ConfigurationError",
    "ParserError",
    "NotifierError",
    "CommandExecutionError",
    "UnsupportedPlatformError",
]
