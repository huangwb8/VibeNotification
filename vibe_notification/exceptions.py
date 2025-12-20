"""
自定义异常类

定义项目中使用的所有自定义异常，统一异常处理
"""

from typing import List

class VibeNotificationError(Exception):
    """VibeNotification 基础异常类"""
    pass

class ConfigurationError(VibeNotificationError):
    """配置相关错误"""
    pass

class ParserError(VibeNotificationError):
    """解析器相关错误"""
    pass

class NotifierError(VibeNotificationError):
    """通知器相关错误"""
    pass

class CommandExecutionError(VibeNotificationError):
    """命令执行相关错误"""
    def __init__(self, command: List[str], return_code: int, error_output: str = ""):
        self.command = command
        self.return_code = return_code
        self.error_output = error_output
        message = f"Command failed: {' '.join(command)} (exit code: {return_code})"
        if error_output:
            message += f" - {error_output}"
        super().__init__(message)

class UnsupportedPlatformError(VibeNotificationError):
    """不支持的平台错误"""
    def __init__(self, platform: str):
        self.platform = platform
        super().__init__(f"Unsupported platform: {platform}")