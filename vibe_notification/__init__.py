"""
VibeNotification - 为 Claude Code 和 Codex 提供智能会话结束通知

主要功能：
1. 检测 Claude Code 和 Codex 的会话结束事件
2. 跨平台系统通知（macOS、Linux、Windows）
3. 智能声音提示
4. 可配置的通知行为
5. 详细的日志记录
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# 主要导出
from .core import VibeNotifier
from .models import NotificationConfig, NotificationEvent, NotificationLevel, PlatformType
from .config import load_config, save_config
from .cli import main

__all__ = [
    "VibeNotifier",
    "NotificationConfig",
    "NotificationEvent",
    "NotificationLevel",
    "PlatformType",
    "load_config",
    "save_config",
    "main",
]