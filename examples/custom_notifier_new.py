#!/usr/bin/env python3
"""
自定义通知器示例 (新包结构)

这个示例展示了如何使用新的包结构创建自定义的 VibeNotifier 实例，
并进行高级配置和使用。
"""

import sys
import os
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from vibe_notification import VibeNotifier, NotificationConfig, NotificationEvent, NotificationLevel
from vibe_notification.notifiers import SoundNotifier, SystemNotifier


def example_custom_config():
    """示例：自定义配置"""
    print("示例 1: 自定义配置")

    # 创建自定义配置
    config = NotificationConfig(
        enable_sound=True,
        enable_notification=True,
        notification_timeout=8000,  # 8秒
        sound_type="default",
        log_level="INFO",
        detect_conversation_end=True
    )

    # 创建通知器
    notifier = VibeNotifier(config)

    # 创建自定义事件
    event = NotificationEvent(
        type="custom-event",
        agent="custom-agent",
        message="这是一个自定义通知示例",
        summary="自定义通知演示",
        timestamp=datetime.now().isoformat(),
        conversation_end=True,
        is_last_turn=True,
        metadata={"custom_field": "custom_value"}
    )

    # 发送通知
    notifier.process_event(event)

    print("✓ 自定义配置示例完成")


def example_multiple_notifications():
    """示例：发送多个通知"""
    print("\n示例 2: 发送多个不同级别的通知")

    config = NotificationConfig()
    notifier = VibeNotifier(config)

    # 创建多个事件
    events = [
        NotificationEvent(
            type="info",
            agent="test-agent",
            message="这是一个信息级别的通知",
            summary="信息通知",
            timestamp=datetime.now().isoformat(),
            conversation_end=False,
            level=NotificationLevel.INFO
        ),
        NotificationEvent(
            type="success",
            agent="test-agent",
            message="操作成功完成！",
            summary="成功通知",
            timestamp=datetime.now().isoformat(),
            conversation_end=True,
            level=NotificationLevel.SUCCESS
        ),
        NotificationEvent(
            type="warning",
            agent="test-agent",
            message="请注意，有警告信息",
            summary="警告通知",
            timestamp=datetime.now().isoformat(),
            conversation_end=False,
            level=NotificationLevel.WARNING
        ),
        NotificationEvent(
            type="error",
            agent="test-agent",
            message="发生了一个错误",
            summary="错误通知",
            timestamp=datetime.now().isoformat(),
            conversation_end=True,
            level=NotificationLevel.ERROR
        ),
    ]

    for event in events:
        print(f"  发送: {event.summary}")
        notifier.process_event(event)

    print("✓ 多级别通知示例完成")


def example_selective_sound():
    """示例：选择性播放声音"""
    print("\n示例 3: 选择性播放声音")

    # 配置：只在会话结束时播放声音
    config = NotificationConfig(
        enable_sound=True,
        enable_notification=True,
        log_level="INFO"
    )

    notifier = VibeNotifier(config)

    # 会话结束事件 - 播放声音
    end_event = NotificationEvent(
        type="agent-turn-complete",
        agent="claude-code",
        message="会话结束",
        summary="Claude Code 会话已结束",
        timestamp=datetime.now().isoformat(),
        conversation_end=True,
        is_last_turn=True
    )

    print("  发送会话结束通知（带声音）...")
    notifier.process_event(end_event)

    # 普通事件 - 不播放声音（通过临时禁用）
    notifier.config.enable_sound = False

    normal_event = NotificationEvent(
        type="agent-turn-complete",
        agent="claude-code",
        message="普通操作",
        summary="完成了一个普通操作",
        timestamp=datetime.now().isoformat(),
        conversation_end=False,
        is_last_turn=False
    )

    print("  发送普通通知（无声音）...")
    notifier.process_event(normal_event)

    print("✓ 选择性声音示例完成")


def example_custom_notifier_class():
    """示例：自定义通知器类"""
    print("\n示例 4: 自定义通知器类")

    class CustomVibeNotifier(VibeNotifier):
        """自定义通知器，扩展功能"""

        def _setup_notifiers(self):
            """自定义通知器设置"""
            # 只使用系统通知，不使用声音
            self.notifiers = [
                SystemNotifier(self.config),
            ]

        def build_notification_content(self, event: NotificationEvent):
            """自定义通知内容构建"""
            title = f"[自定义] {event.agent} — {'会话结束' if event.conversation_end else '操作完成'}"
            message = event.summary or event.message or "通知"
            subtitle = f"工具: {event.tool_name}" if event.tool_name else event.agent

            # 自定义级别映射
            if event.conversation_end:
                level = NotificationLevel.SUCCESS
            elif event.type == "error":
                level = NotificationLevel.ERROR
            else:
                level = NotificationLevel.INFO

            return title, message, subtitle, level

    # 使用自定义通知器
    config = NotificationConfig(enable_sound=False)  # 禁用声音
    custom_notifier = CustomVibeNotifier(config)

    # 测试事件
    event = NotificationEvent(
        type="custom-operation",
        agent="my-tool",
        message="完成了自定义操作",
        summary="自定义操作已完成",
        timestamp=datetime.now().isoformat(),
        tool_name="CustomTool",
        conversation_end=True,
        is_last_turn=True
    )

    print(f"  使用自定义通知器处理事件: {event.agent} - {event.type}")
    custom_notifier.process_event(event)

    print("✓ 自定义通知器类示例完成")


def example_direct_notifier_usage():
    """示例：直接使用通知器"""
    print("\n示例 5: 直接使用通知器")

    config = NotificationConfig()

    # 直接创建和使用通知器
    sound_notifier = SoundNotifier(config)
    system_notifier = SystemNotifier(config)

    # 测试声音通知器
    if sound_notifier.is_enabled():
        print("  测试声音通知器...")
        sound_notifier.notify("测试声音", "这是一个测试声音通知", NotificationLevel.INFO)

    # 测试系统通知器
    if system_notifier.is_enabled():
        print("  测试系统通知器...")
        system_notifier.notify(
            "测试系统通知",
            "这是一个测试系统通知",
            NotificationLevel.INFO,
            subtitle="测试副标题"
        )

    print("✓ 直接通知器使用示例完成")


def example_config_management():
    """示例：配置管理"""
    print("\n示例 6: 配置管理")

    from vibe_notification.config import load_config, save_config

    # 加载配置
    config = load_config()
    print(f"  当前配置:")
    print(f"    声音通知: {'启用' if config.enable_sound else '禁用'}")
    print(f"    系统通知: {'启用' if config.enable_notification else '禁用'}")
    print(f"    日志级别: {config.log_level}")

    # 修改配置
    config.enable_sound = True
    config.notification_timeout = 10000

    # 保存配置
    save_config(config)
    print("  配置已保存")

    print("✓ 配置管理示例完成")


def main():
    """运行所有示例"""
    print("=" * 60)
    print("VibeNotification 示例集 (新包结构)")
    print("=" * 60)

    try:
        example_custom_config()
        example_multiple_notifications()
        example_selective_sound()
        example_custom_notifier_class()
        example_direct_notifier_usage()
        example_config_management()

        print("\n" + "=" * 60)
        print("所有示例运行完成！ 🎉")
        print("=" * 60)

    except Exception as e:
        print(f"\n示例运行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())