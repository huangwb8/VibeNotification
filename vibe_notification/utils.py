"""
工具函数模块

包含通用的工具函数
"""

import shutil
import platform
from typing import Optional
from .models import PlatformType


def detect_platform() -> PlatformType:
    """检测当前平台"""
    system = platform.system().lower()
    if system == "darwin":
        return PlatformType.MACOS
    elif system == "linux":
        return PlatformType.LINUX
    elif system == "windows":
        return PlatformType.WINDOWS
    else:
        return PlatformType.UNKNOWN


def command_exists(cmd: str) -> bool:
    """检查命令是否在 PATH 中"""
    try:
        return shutil.which(cmd) is not None
    except Exception:
        return False


def truncate_text(text: str, max_length: int = 240) -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def escape_for_osascript(text: str) -> str:
    """为 AppleScript 转义文本"""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def escape_for_powershell(text: str) -> str:
    """为 PowerShell 转义文本"""
    return text.replace("'", "''")