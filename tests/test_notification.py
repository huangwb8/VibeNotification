#!/usr/bin/env python3
"""
Windows 通知链路的手工验证测试。

默认跳过，避免在非 Windows / 非交互环境里直接调用 PowerShell。
如需手工验证，可运行：
    VIBE_NOTIFICATION_RUN_WINDOWS_TEST=1 pytest tests/test_notification.py -q -s
"""

from __future__ import annotations

import os
import shutil

import pytest

from vibe_notification.adapters import DefaultCommandExecutor, WindowsAdapter


def test_notification():
    if os.environ.get("VIBE_NOTIFICATION_RUN_WINDOWS_TEST") != "1":
        pytest.skip("需要设置 VIBE_NOTIFICATION_RUN_WINDOWS_TEST=1 才运行手工 Windows 通知测试")

    if not shutil.which("powershell.exe"):
        pytest.skip("当前环境没有 powershell.exe")

    executor = DefaultCommandExecutor()
    adapter = WindowsAdapter(executor)

    title = "VibeNotification 测试"
    message = "这是一个测试消息"
    subtitle = "WSL测试"

    adapter.show_notification(title, message, subtitle)
