"""
测试异常模块
"""

import pytest
from vibe_notification.exceptions import (
    VibeNotificationError,
    ConfigurationError,
    ParserError,
    NotifierError,
    CommandExecutionError,
    UnsupportedPlatformError
)


class TestVibeNotificationError:
    """测试基础异常类"""

    def test_inheritance(self):
        """测试继承关系"""
        error = VibeNotificationError("Test message")
        assert isinstance(error, Exception)
        assert str(error) == "Test message"


class TestConfigurationError:
    """测试配置错误"""

    def test_inheritance(self):
        """测试继承关系"""
        error = ConfigurationError("Config error")
        assert isinstance(error, VibeNotificationError)
        assert isinstance(error, Exception)

    def test_message(self):
        """测试错误消息"""
        error = ConfigurationError("Invalid configuration")
        assert str(error) == "Invalid configuration"


class TestParserError:
    """测试解析器错误"""

    def test_inheritance(self):
        """测试继承关系"""
        error = ParserError("Parse error")
        assert isinstance(error, VibeNotificationError)
        assert isinstance(error, Exception)

    def test_message(self):
        """测试错误消息"""
        error = ParserError("Failed to parse input")
        assert str(error) == "Failed to parse input"


class TestNotifierError:
    """测试通知器错误"""

    def test_inheritance(self):
        """测试继承关系"""
        error = NotifierError("Notify error")
        assert isinstance(error, VibeNotificationError)
        assert isinstance(error, Exception)

    def test_message(self):
        """测试错误消息"""
        error = NotifierError("Failed to send notification")
        assert str(error) == "Failed to send notification"


class TestCommandExecutionError:
    """测试命令执行错误"""

    def test_inheritance(self):
        """测试继承关系"""
        error = CommandExecutionError(["echo", "test"], 1)
        assert isinstance(error, VibeNotificationError)
        assert isinstance(error, Exception)

    def test_basic(self):
        """测试基本属性"""
        command = ["echo", "test"]
        return_code = 1
        error = CommandExecutionError(command, return_code)

        assert error.command == command
        assert error.return_code == return_code
        assert error.error_output == ""
        assert "echo test" in str(error)
        assert "exit code: 1" in str(error)

    def test_with_error_output(self):
        """测试带错误输出的错误"""
        command = ["invalid", "command"]
        return_code = 127
        error_output = "command not found"

        error = CommandExecutionError(command, return_code, error_output)

        assert error.error_output == error_output
        assert error_output in str(error)

    def test_complex_command(self):
        """测试复杂命令的格式化"""
        command = ["python", "-m", "vibe_notification", "--config", "test.json"]
        return_code = 2

        error = CommandExecutionError(command, return_code)

        assert "python -m vibe_notification --config test.json" in str(error)


class TestUnsupportedPlatformError:
    """测试不支持的平台错误"""

    def test_inheritance(self):
        """测试继承关系"""
        error = UnsupportedPlatformError("UnknownOS")
        assert isinstance(error, VibeNotificationError)
        assert isinstance(error, Exception)

    def test_attributes(self):
        """测试属性"""
        platform = "UnknownOS"
        error = UnsupportedPlatformError(platform)

        assert error.platform == platform
        assert platform in str(error)
        assert "Unsupported platform" in str(error)

    def test_with_real_platform_names(self):
        """测试真实平台名称"""
        platforms = ["FreeBSD", "OpenBSD", "SunOS"]
        for platform in platforms:
            error = UnsupportedPlatformError(platform)
            assert str(error) == f"Unsupported platform: {platform}"
            assert error.platform == platform