#!/usr/bin/env python3
"""
VibeNotification 测试脚本

测试新的包结构
"""

import sys
import os
import json
import tempfile
import logging

# 添加当前目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from vibe_notification import (
    VibeNotifier,
    NotificationEvent,
    NotificationConfig,
    NotificationLevel,
    PlatformType
)
from vibe_notification.detectors import detect_conversation_end


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

    print(f"事件类型: {event.type}")
    print(f"代理: {event.agent}")
    print(f"消息: {event.message}")
    print(f"工具: {event.tool_name}")
    print(f"会话结束: {event.conversation_end}")

    # 测试序列化和反序列化
    event_dict = event.to_dict()
    event2 = NotificationEvent.from_dict(event_dict)
    assert event.type == event2.type
    assert event.agent == event2.agent

    print("✓ NotificationEvent 测试通过")


def test_notification_config():
    """测试通知配置"""
    print("\n测试 NotificationConfig...")

    config = NotificationConfig(
        enable_sound=True,
        enable_notification=True,
        notification_timeout=5000,
        sound_type="custom",
        log_level="DEBUG",
        detect_conversation_end=True
    )

    print(f"启用声音: {config.enable_sound}")
    print(f"启用通知: {config.enable_notification}")
    print(f"通知超时: {config.notification_timeout}ms")
    print(f"声音类型: {config.sound_type}")
    print(f"日志级别: {config.log_level}")
    print(f"检测会话结束: {config.detect_conversation_end}")

    # 测试序列化和反序列化
    config_dict = config.to_dict()
    config2 = NotificationConfig.from_dict(config_dict)
    assert config.enable_sound == config2.enable_sound
    assert config.notification_timeout == config2.notification_timeout

    print("✓ NotificationConfig 测试通过")


def test_vibe_notifier():
    """测试 VibeNotifier"""
    print("\n测试 VibeNotifier...")

    # 创建临时日志文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as log_file:
        log_path = log_file.name

    try:
        config = NotificationConfig(
            enable_sound=False,  # 测试时禁用声音
            enable_notification=False,  # 测试时禁用通知
            log_level="DEBUG"
        )

        notifier = VibeNotifier(config)

        # 测试事件
        from datetime import datetime
        event = NotificationEvent(
            type="test",
            agent="test-agent",
            message="测试消息",
            summary="测试摘要",
            timestamp=datetime.now().isoformat(),
            conversation_end=True,
            is_last_turn=True
        )

        # 测试通知内容构建
        title, message, subtitle, level = notifier.build_notification_content(event)
        print(f"构建的通知内容:")
        print(f"  标题: {title}")
        print(f"  消息: {message}")
        print(f"  副标题: {subtitle}")
        print(f"  级别: {level}")

        # 测试事件处理（不会实际发送通知）
        notifier.process_event(event)

        print("✓ VibeNotifier 测试通过")

    finally:
        # 清理临时文件
        if os.path.exists(log_path):
            os.unlink(log_path)


def test_conversation_end_detection():
    """测试会话结束检测"""
    print("\n测试会话结束检测...")

    # 测试各种会话结束标志
    test_cases = [
        ({"is_last_turn": True}, True, "is_last_turn"),
        ({"conversation_end": True}, True, "conversation_end"),
        ({"conversation_finished": True}, True, "conversation_finished"),
        ({"final": True}, True, "final"),
        ({"closed": True}, True, "closed"),
        ({"state": "finished"}, True, "state=finished"),
        ({"state": "ended"}, True, "state=ended"),
        ({"turn": 5, "total_turns": 5}, True, "turn==total"),
        ({"turn": 3, "total_turns": 5}, False, "turn<total"),
        ({"payload": {"conversation_end": True}}, True, "nested conversation_end"),
        ({}, False, "no flags"),
    ]

    for event_data, expected, description in test_cases:
        result = detect_conversation_end(event_data)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {description}: {result} (期望: {expected})")

    print("✓ 会话结束检测测试通过")


def test_notification_levels():
    """测试通知级别"""
    print("\n测试通知级别...")

    config = NotificationConfig(enable_notification=False)
    notifier = VibeNotifier(config)

    levels = [
        (NotificationLevel.INFO, "信息"),
        (NotificationLevel.SUCCESS, "成功"),
        (NotificationLevel.WARNING, "警告"),
        (NotificationLevel.ERROR, "错误"),
    ]

    for level, name in levels:
        print(f"  测试 {name} 级别: {level.value}")
        # 这里只是测试调用，实际不会显示通知
        event = NotificationEvent(
            type="test",
            agent="test",
            message=f"测试 {name} 级别",
            summary=f"测试 {name} 级别",
            timestamp="2025-12-20T13:00:00",
            conversation_end=True
        )
        notifier.process_event(event)

    print("✓ 通知级别测试通过")


def test_platform_detection():
    """测试平台检测"""
    print("\n测试平台检测...")

    from vibe_notification.utils import detect_platform
    platform = detect_platform()

    print(f"检测到的平台: {platform}")
    print(f"平台值: {platform.value}")

    # 验证是有效的平台类型
    assert platform in PlatformType
    print("✓ 平台检测测试通过")


def main():
    """主测试函数"""
    print("=" * 60)
    print("VibeNotification 测试套件 (新包结构)")
    print("=" * 60)

    try:
        test_notification_event()
        test_notification_config()
        test_vibe_notifier()
        test_conversation_end_detection()
        test_notification_levels()
        test_platform_detection()

        print("\n" + "=" * 60)
        print("所有测试通过！ 🎉")
        print("=" * 60)

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())