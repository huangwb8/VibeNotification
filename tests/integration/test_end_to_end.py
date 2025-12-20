"""
端到端集成测试
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch
from vibe_notification import VibeNotifier
from vibe_notification.models import NotificationConfig
from vibe_notification.config import save_config, load_config


class TestEndToEnd:
    """端到端测试"""

    @pytest.fixture
    def temp_config_file(self):
        """创建临时配置文件"""
        config_data = {
            "enable_sound": True,
            "enable_notification": True,
            "sound_type": "default",
            "notification_timeout": 5000,
            "log_level": "DEBUG"
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)

        yield temp_path

        # 清理
        temp_path.unlink(missing_ok=True)

    def test_complete_flow_with_mock_parsers(self, mock_config):
        """测试完整流程（使用模拟解析器）"""
        # 创建模拟的事件
        from datetime import datetime
        from vibe_notification.models import NotificationEvent

        mock_event = NotificationEvent(
            type="conversation_end",
            agent="claude-code",
            message="测试消息",
            summary="测试摘要",
            timestamp=datetime.now().isoformat(),
            conversation_end=True,
            is_last_turn=True,
            tool_name="test-tool"
        )

        with patch('vibe_notification.parsers.CodexParser') as MockParser:
            # 配置模拟解析器
            parser_instance = MockParser.return_value
            parser_instance.can_parse.return_value = True
            parser_instance.parse.return_value = mock_event

            # 模拟平台适配器
            with patch('vibe_notification.adapters.create_platform_adapter') as mock_adapter:
                mock_adapter.return_value = Mock()
                mock_adapter.return_value.is_sound_available.return_value = True
                mock_adapter.return_value.is_notification_available.return_value = True

                # 运行 VibeNotifier
                notifier = VibeNotifier(mock_config)
                notifier.run()

                # 验证解析器被调用
                parser_instance.can_parse.assert_called_once()
                parser_instance.parse.assert_called_once()

    def test_config_save_and_load(self, temp_config_file):
        """测试配置保存和加载"""
        # 创建配置
        config = NotificationConfig(
            enable_sound=True,
            enable_notification=False,
            sound_type="custom",
            notification_timeout=10000,
            log_level="DEBUG"
        )

        # 保存配置
        save_config(config, temp_config_file)

        # 加载配置
        loaded_config = load_config(temp_config_file)

        # 验证配置
        assert loaded_config.enable_sound is True
        assert loaded_config.enable_notification is False
        assert loaded_config.sound_type == "custom"
        assert loaded_config.notification_timeout == 10000
        assert loaded_config.log_level == "DEBUG"

    def test_error_handling_flow(self, mock_config):
        """测试错误处理流程"""
        with patch('vibe_notification.parsers.CodexParser') as MockParser:
            # 配置解析器抛出异常
            parser_instance = MockParser.return_value
            parser_instance.can_parse.return_value = True
            parser_instance.parse.side_effect = Exception("Parse error")

            # 模拟平台适配器
            with patch('vibe_notification.adapters.create_platform_adapter') as mock_adapter:
                mock_adapter.return_value = Mock()
                mock_adapter.return_value.is_sound_available.return_value = True
                mock_adapter.return_value.is_notification_available.return_value = True

                # 运行 VibeNotifier
                notifier = VibeNotifier(mock_config)

                # 应该抛出异常
                with pytest.raises(Exception):
                    notifier.run()

    def test_no_parser_available(self, mock_config):
        """测试没有可用解析器的情况"""
        with patch('vibe_notification.parsers.CodexParser') as MockParser, \
             patch('vibe_notification.parsers.ClaudeCodeParser') as MockClaudeParser:

            # 配置所有解析器都不可用
            MockParser.return_value.can_parse.return_value = False
            MockClaudeParser.return_value.can_parse.return_value = False

            # 模拟平台适配器
            with patch('vibe_notification.adapters.create_platform_adapter') as mock_adapter:
                mock_adapter.return_value = Mock()
                mock_adapter.return_value.is_sound_available.return_value = True
                mock_adapter.return_value.is_notification_available.return_value = True

                # 运行 VibeNotifier
                notifier = VibeNotifier(mock_config)
                notifier.run()

                # 应该使用测试事件，而不是崩溃
                # 没有断言，不抛出异常就说明成功

    def test_disabled_notifiers(self, mock_config):
        """测试禁用通知器的情况"""
        # 禁用所有通知器
        mock_config.enable_sound = False
        mock_config.enable_notification = False

        from datetime import datetime
        from vibe_notification.models import NotificationEvent

        mock_event = NotificationEvent(
            type="conversation_end",
            agent="claude-code",
            message="测试消息",
            summary="测试摘要",
            timestamp=datetime.now().isoformat(),
            conversation_end=True,
            is_last_turn=True,
            tool_name="test-tool"
        )

        with patch('vibe_notification.parsers.CodexParser') as MockParser:
            parser_instance = MockParser.return_value
            parser_instance.can_parse.return_value = True
            parser_instance.parse.return_value = mock_event

            # 模拟平台适配器
            with patch('vibe_notification.adapters.create_platform_adapter') as mock_adapter:
                adapter = Mock()
                adapter.is_sound_available.return_value = False
                adapter.is_notification_available.return_value = False
                mock_adapter.return_value = adapter

                # 运行 VibeNotifier
                notifier = VibeNotifier(mock_config)
                notifier.run()

                # 验证适配器方法未被调用
                adapter.play_sound.assert_not_called()
                adapter.show_notification.assert_not_called()

    def test_platform_adapter_creation(self):
        """测试平台适配器创建"""
        # 测试不同的平台
        platforms = [
            ("Darwin", "MacOSAdapter"),
            ("Linux", "LinuxAdapter"),
            ("Windows", "WindowsAdapter")
        ]

        for platform_name, adapter_class in platforms:
            with patch('vibe_notification.utils.get_platform_info') as mock_get_platform:
                mock_get_platform.return_value = {"system": platform_name}

                from vibe_notification.factories import AdapterFactory
                adapter = AdapterFactory.create_platform_adapter()

                # 验证创建了正确的适配器类型
                assert adapter.__class__.__name__ == adapter_class

    def test_unsupported_platform(self):
        """测试不支持的平台"""
        with patch('vibe_notification.utils.get_platform_info') as mock_get_platform:
            mock_get_platform.return_value = {"system": "UnknownOS"}

            from vibe_notification.factories import AdapterFactory
            from vibe_notification.exceptions import UnsupportedPlatformError

            with pytest.raises(UnsupportedPlatformError):
                AdapterFactory.create_platform_adapter()