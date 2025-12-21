#!/usr/bin/env python3
"""
测试Windows通知系统
"""

import subprocess
import sys
sys.path.insert(0, 'vibe_notification')

from vibe_notification.adapters import WindowsAdapter, DefaultCommandExecutor
from vibe_notification.models import NotificationConfig

def test_notification():
    # 创建配置
    config = NotificationConfig()

    # 创建Windows适配器
    executor = DefaultCommandExecutor()
    adapter = WindowsAdapter(executor)

    print(f"PowerShell可用: {adapter.is_notification_available()}")

    # 发送测试通知
    title = "VibeNotification 测试"
    message = "这是一个测试消息"
    subtitle = "WSL测试"

    print(f"发送通知: {title} - {message}")
    adapter.show_notification(title, message, subtitle)
    print("通知命令已执行")

if __name__ == "__main__":
    test_notification()