"""
测试工厂模块
"""

import pytest
from unittest.mock import Mock, patch
from vibe_notification.models import NotificationConfig
from vibe_notification.factories import (
    ParserFactory,
    NotifierFactory,
    AdapterFactory
)
from vibe_notification.parsers import BaseParser, ClaudeCodeParser, CodexParser
from vibe_notification.notifiers import BaseNotifier, SoundNotifier, SystemNotifier
from vibe_notification.adapters import PlatformAdapter, DefaultCommandExecutor
from tests.conftest import mock_config


class TestParserFactory:
    """测试解析器工厂"""

    def test_create_default_parsers(self):
        """测试创建默认解析器列表"""
        parsers = ParserFactory.create_default_parsers()

        assert len(parsers) > 0
        assert all(isinstance(p, BaseParser) for p in parsers)
        assert any(isinstance(p, CodexParser) for p in parsers)
        assert any(isinstance(p, ClaudeCodeParser) for p in parsers)

    def test_create_parser_codex(self):
        """测试创建 Codex 解析器"""
        parser = ParserFactory.create_parser("codex")

        assert isinstance(parser, CodexParser)

    def test_create_parser_claude_code(self):
        """测试创建 Claude Code 解析器"""
        parser = ParserFactory.create_parser("claude_code")

        assert isinstance(parser, ClaudeCodeParser)

    def test_create_parser_invalid(self):
        """测试创建无效类型的解析器"""
        with pytest.raises(ValueError, match="Unknown parser type"):
            ParserFactory.create_parser("invalid_type")

    def test_create_parser_case_insensitive(self):
        """测试创建解析器时忽略大小写"""
        parser = ParserFactory.create_parser("CODEX")
        assert isinstance(parser, CodexParser)

        parser = ParserFactory.create_parser("CLAUDE_CODE")
        assert isinstance(parser, ClaudeCodeParser)

    def test_create_custom_parsers_empty(self):
        """测试创建空的自定义解析器列表"""
        parsers = ParserFactory.create_custom_parsers([])
        assert parsers == []

    def test_create_custom_parsers_with_config(self):
        """测试根据配置创建自定义解析器"""
        configs = [
            {"type": "codex"},
            {"type": "claude_code", "config": {"option": "value"}}
        ]

        parsers = ParserFactory.create_custom_parsers(configs)

        assert len(parsers) == 2
        assert isinstance(parsers[0], CodexParser)
        assert isinstance(parsers[1], ClaudeCodeParser)

    def test_create_custom_parsers_invalid_type(self):
        """测试创建自定义解析器时跳过无效类型"""
        configs = [
            {"type": "codex"},
            {"type": "invalid_type"},  # 应该被跳过
            {"type": "claude_code"}
        ]

        parsers = ParserFactory.create_custom_parsers(configs)

        assert len(parsers) == 2
        assert isinstance(parsers[0], CodexParser)
        assert isinstance(parsers[1], ClaudeCodeParser)


class TestNotifierFactory:
    """测试通知器工厂"""

    def test_create_default_notifiers(self, mock_config):
        """测试创建默认通知器列表"""
        mock_adapter = Mock(spec=PlatformAdapter)
        notifiers = NotifierFactory.create_default_notifiers(mock_config, mock_adapter)

        assert len(notifiers) > 0
        assert all(isinstance(n, BaseNotifier) for n in notifiers)
        assert any(isinstance(n, SoundNotifier) for n in notifiers)
        assert any(isinstance(n, SystemNotifier) for n in notifiers)

    def test_create_notifier_sound(self, mock_config):
        """测试创建声音通知器"""
        mock_adapter = Mock(spec=PlatformAdapter)
        notifier = NotifierFactory.create_notifier("sound", mock_config, mock_adapter)

        assert isinstance(notifier, SoundNotifier)

    def test_create_notifier_system(self, mock_config):
        """测试创建系统通知器"""
        mock_adapter = Mock(spec=PlatformAdapter)
        notifier = NotifierFactory.create_notifier("system", mock_config, mock_adapter)

        assert isinstance(notifier, SystemNotifier)

    def test_create_notifier_invalid(self, mock_config):
        """测试创建无效类型的通知器"""
        mock_adapter = Mock(spec=PlatformAdapter)
        with pytest.raises(ValueError, match="Unknown notifier type"):
            NotifierFactory.create_notifier("invalid_type", mock_config, mock_adapter)

    def test_create_notifier_case_insensitive(self, mock_config):
        """测试创建通知器时忽略大小写"""
        mock_adapter = Mock(spec=PlatformAdapter)

        notifier = NotifierFactory.create_notifier("SOUND", mock_config, mock_adapter)
        assert isinstance(notifier, SoundNotifier)

        notifier = NotifierFactory.create_notifier("SYSTEM", mock_config, mock_adapter)
        assert isinstance(notifier, SystemNotifier)

    def test_create_custom_notifiers_empty(self, mock_config):
        """测试创建空的自定义通知器列表"""
        mock_adapter = Mock(spec=PlatformAdapter)
        notifiers = NotifierFactory.create_custom_notifiers([], mock_config, mock_adapter)
        assert notifiers == []

    def test_create_custom_notifiers_with_config(self, mock_config):
        """测试根据配置创建自定义通知器"""
        mock_adapter = Mock(spec=PlatformAdapter)
        configs = [
            {"type": "sound"},
            {"type": "system", "config": {"option": "value"}}
        ]

        notifiers = NotifierFactory.create_custom_notifiers(
            configs, mock_config, mock_adapter
        )

        assert len(notifiers) == 2
        assert isinstance(notifiers[0], SoundNotifier)
        assert isinstance(notifiers[1], SystemNotifier)


class TestAdapterFactory:
    """测试适配器工厂"""

    def test_create_default_executor(self):
        """测试创建默认命令执行器"""
        executor = AdapterFactory.create_default_executor()

        assert isinstance(executor, DefaultCommandExecutor)

    @patch('vibe_notification.adapters.create_platform_adapter')
    @patch('vibe_notification.adapters.DefaultCommandExecutor')
    def test_create_platform_adapter_default_executor(
        self, mock_executor_class, mock_create_adapter
    ):
        """测试使用默认执行器创建平台适配器"""
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        mock_create_adapter.return_value = Mock(spec=PlatformAdapter)

        adapter = AdapterFactory.create_platform_adapter()

        mock_executor_class.assert_called_once()
        mock_create_adapter.assert_called_once_with(mock_executor)

    @patch('vibe_notification.adapters.create_platform_adapter')
    def test_create_platform_adapter_custom_executor(self, mock_create_adapter):
        """测试使用自定义执行器创建平台适配器"""
        mock_executor = Mock(spec=DefaultCommandExecutor)
        mock_create_adapter.return_value = Mock(spec=PlatformAdapter)

        adapter = AdapterFactory.create_platform_adapter(mock_executor)

        mock_create_adapter.assert_called_once_with(mock_executor)