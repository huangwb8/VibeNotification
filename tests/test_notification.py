#!/usr/bin/env python3
"""
VibeNotification 测试脚本
"""

import sys
import os
import json
import tempfile
import logging

from vibe_notification import VibeNotifier, NotificationEvent, NotificationConfig, NotificationLevel
from vibe_notification.detectors import detect_conversation_end, detect_conversation_end_from_hook


def test_notification_event():
    """测试通知事件"""
    print("测试 NotificationEvent...")

    event = NotificationEvent(
        type="agent-turn-complete",
        agent="claude-code",
        message="测试消息",
        summary="测试摘要",
        timestamp="2025-12-20T13:00:00",
        tool_name="Write",
        conversation_end=True,
        is_last_turn=True
    )

    # 测试属性访问
    assert event.type == "agent-turn-complete"
    assert event.agent == "claude-code"
    assert event.message == "测试消息"
    assert event.summary == "测试摘要"
    assert event.timestamp == "2025-12-20T13:00:00"
    assert event.tool_name == "Write"
    assert event.conversation_end is True
    assert event.is_last_turn is True

    # 测试 to_dict 方法
    event_dict = event.to_dict()
    assert isinstance(event_dict, dict)
    assert event_dict["type"] == "agent-turn-complete"
    assert event_dict["agent"] == "claude-code"

    print("✅ NotificationEvent 测试通过")


def test_notification_config():
    """测试通知配置"""
    print("测试 NotificationConfig...")

    config = NotificationConfig(
        enable_sound=True,
        enable_notification=True,
        notification_timeout=10000,
        sound_type="default",
        log_level="INFO",
        detect_conversation_end=True
    )

    # 测试属性访问
    assert config.enable_sound is True
    assert config.enable_notification is True
    assert config.notification_timeout == 10000
    assert config.sound_type == "default"
    assert config.log_level == "INFO"
    assert config.detect_conversation_end is True

    # 测试默认值
    default_config = NotificationConfig()
    assert default_config.enable_sound is True
    assert default_config.enable_notification is True
    assert default_config.notification_timeout == 10000
    assert default_config.sound_type == "default"
    assert default_config.log_level == "INFO"
    assert default_config.detect_conversation_end is True

    print("✅ NotificationConfig 测试通过")


def test_vibe_notifier():
    """测试 VibeNotifier"""
    print("测试 VibeNotifier...")

    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_data = {
            "enable_sound": False,
            "enable_notification": True,
            "notification_timeout": 5000,
            "sound_type": "custom",
            "log_level": "DEBUG",
            "detect_conversation_end": False
        }
        json.dump(config_data, f)
        config_file = f.name

    try:
        # 测试从文件加载配置
        from vibe_notification.config import load_config
        config = load_config(config_file)
        notifier = VibeNotifier(config)
        assert notifier.config.enable_sound is False
        assert notifier.config.enable_notification is True
        assert notifier.config.notification_timeout == 5000
        assert notifier.config.sound_type == "custom"
        assert notifier.config.log_level == "DEBUG"
        assert notifier.config.detect_conversation_end is False

        print("✅ VibeNotifier 配置加载测试通过")

        # 测试事件处理
        event = NotificationEvent(
            type="test-event",
            agent="test-agent",
            message="测试消息",
            summary="测试摘要",
            timestamp="2025-12-20T13:00:00",
            conversation_end=True
        )

        # 注意：在实际测试中，这里可能会弹出系统通知
        # 我们可以设置日志级别来避免干扰
        notifier.logger.setLevel(logging.ERROR)
        notifier.process_event(event)

        print("✅ VibeNotifier 事件处理测试通过")

    finally:
        # 清理临时文件
        os.unlink(config_file)


def test_notification_level():
    """测试通知级别"""
    print("测试 NotificationLevel...")

    assert NotificationLevel.INFO.value == "INFO"
    assert NotificationLevel.SUCCESS.value == "SUCCESS"
    assert NotificationLevel.WARNING.value == "WARNING"
    assert NotificationLevel.ERROR.value == "ERROR"

    # 测试字符串转换
    assert str(NotificationLevel.INFO) == "INFO"
    assert str(NotificationLevel.SUCCESS) == "SUCCESS"
    assert str(NotificationLevel.WARNING) == "WARNING"
    assert str(NotificationLevel.ERROR) == "ERROR"

    print("✅ NotificationLevel 测试通过")


def test_detect_conversation_end_turn_complete():
    """测试 agent turn 完成的会话结束检测"""
    event = {"type": "agent-turn-complete", "agent": "codex"}
    assert detect_conversation_end(event) is True

    hook_data = {"toolName": "Write"}
    assert detect_conversation_end_from_hook(hook_data) is True


def test_detect_conversation_end_assistant_role():
    """测试助手角色输出完成的检测"""
    event = {"role": "assistant", "display": "how are you?", "partial": False}
    assert detect_conversation_end(event) is True


def main():
    """运行所有测试"""
    print("开始运行 VibeNotification 测试...\n")

    try:
        test_notification_event()
        print()

        test_notification_config()
        print()

        test_vibe_notifier()
        print()

        test_notification_level()
        print()

        print("🎉 所有测试通过！")
        return 0

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
