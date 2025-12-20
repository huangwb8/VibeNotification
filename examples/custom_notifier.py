#!/usr/bin/env python3
"""
自定义通知器示例

这个示例展示了如何创建自定义的 VibeNotifier 实例，
并进行高级配置和使用。
"""

import sys
import os
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from vibe_notification import VibeNotifier, NotificationConfig, NotificationEvent, NotificationLevel


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

    notifier = VibeNotifier(NotificationConfig())

    notifications = [
        ("信息通知", "这是一个信息级别的通知", NotificationLevel.INFO),
        ("成功通知", "操作成功完成！", NotificationLevel.SUCCESS),
        ("警告通知", "请注意，有警告信息", NotificationLevel.WARNING),
        ("错误通知", "发生了一个错误", NotificationLevel.ERROR),
    ]

    for title, message, level in notifications:
        print(f"  发送: {title}")
        notifier.show_notification(title, message, level=level)

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


def example_custom_event_parsing():
    """示例：自定义事件解析"""
    print("\n示例 4: 自定义事件解析")

    class CustomNotifier(VibeNotifier):
        """自定义通知器，扩展事件解析"""

        def parse_custom_event(self, event_data: dict) -> NotificationEvent:
            """解析自定义事件格式"""
            # 自定义逻辑：检测重要事件
            is_important = event_data.get("importance", "normal") == "high"

            event = NotificationEvent(
                type=event_data.get("type", "custom"),
                agent=event_data.get("agent", "custom-agent"),
                message=event_data.get("message", ""),
                summary=event_data.get("summary", ""),
                timestamp=event_data.get("timestamp", datetime.now().isoformat()),
                conversation_end=event_data.get("conversation_end", False),
                is_last_turn=event_data.get("is_last_turn", False),
                metadata=event_data
            )

            # 如果是重要事件，标记为会话结束
            if is_important:
                event.conversation_end = True
                event.is_last_turn = True

            return event

    # 使用自定义通知器
    notifier = CustomNotifier()

    # 自定义事件数据
    custom_data = {
        "type": "custom-operation",
        "agent": "my-tool",
        "message": "完成了重要操作",
        "summary": "重要操作已完成",
        "importance": "high",  # 自定义字段
        "custom_field": "custom_value"
    }

    # 解析并处理
    event = notifier.parse_custom_event(custom_data)
    print(f"  解析的事件: {event.agent} - {event.type}")
    print(f"  是否重要: {event.conversation_end}")

    notifier.process_event(event)

    print("✓ 自定义事件解析示例完成")


def example_integration_with_other_tools():
    """示例：与其他工具集成"""
    print("\n示例 5: 与其他工具集成")

    notifier = VibeNotifier()

    # 模拟从其他工具接收事件
    def handle_tool_completion(tool_name: str, success: bool, details: dict):
        """处理工具完成事件"""
        if success:
            title = f"工具完成: {tool_name}"
            message = f"{tool_name} 操作成功完成"
            level = NotificationLevel.SUCCESS
        else:
            title = f"工具失败: {tool_name}"
            message = f"{tool_name} 操作失败: {details.get('error', '未知错误')}"
            level = NotificationLevel.ERROR

        notifier.show_notification(title, message, level=level)

    # 测试工具完成事件
    print("  模拟工具完成事件...")
    handle_tool_completion("DataProcessor", True, {"records": 100})
    handle_tool_completion("FileUploader", False, {"error": "网络连接失败"})

    print("✓ 工具集成示例完成")


def main():
    """运行所有示例"""
    print("=" * 60)
    print("VibeNotification 示例集")
    print("=" * 60)

    try:
        example_custom_config()
        example_multiple_notifications()
        example_selective_sound()
        example_custom_event_parsing()
        example_integration_with_other_tools()

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