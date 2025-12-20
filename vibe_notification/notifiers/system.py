"""
系统通知器

负责显示系统通知
"""

import subprocess
import sys
from typing import Optional
from .base import BaseNotifier
from ..models import NotificationConfig, NotificationLevel
from ..utils import command_exists, detect_platform, escape_for_osascript, escape_for_powershell
from ..models import PlatformType


class SystemNotifier(BaseNotifier):
    """系统通知器"""

    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self.config.enable_notification

    def notify(self, title: str, message: str, level: NotificationLevel = NotificationLevel.INFO, **kwargs):
        """显示系统通知"""
        if not self.is_enabled():
            return

        subtitle = kwargs.get("subtitle", "")
        self.log_notification(title, message, level)

        try:
            platform_type = detect_platform()
            if platform_type == PlatformType.MACOS:
                self._notify_macos(title, message, subtitle, level)
            elif platform_type == PlatformType.LINUX:
                self._notify_linux(title, message, level)
            elif platform_type == PlatformType.WINDOWS:
                self._notify_windows(title, message, level)
        except Exception as e:
            self.logger.warning(f"显示通知失败: {e}")
            # 回退到打印
            print(f"[VibeNotification] {title}: {message}", file=sys.stderr)

    def _notify_macos(self, title: str, message: str, subtitle: str, level: NotificationLevel):
        """macOS 显示通知"""
        # 优先使用 terminal-notifier，避免部分环境下 osascript 权限/语法问题
        if command_exists("terminal-notifier"):
            args = [
                "terminal-notifier",
                "-title",
                title,
                "-message",
                message,
                "-sound",
                "Glass",
            ]
            if subtitle:
                args.extend(["-subtitle", subtitle])
            subprocess.Popen(args)
            return

        esc_msg = escape_for_osascript(message)
        esc_title = escape_for_osascript(title)
        esc_sub = escape_for_osascript(subtitle)

        script = f'display notification "{esc_msg}" with title "{esc_title}"'
        if esc_sub:
            script += f' subtitle "{esc_sub}"'
        script += ' sound name "Glass"'

        subprocess.Popen(["osascript", "-e", script])

    def _notify_linux(self, title: str, message: str, level: NotificationLevel):
        """Linux 显示通知"""
        # 尝试 notify-send
        if command_exists("notify-send"):
            urgency = "normal"
            if level == NotificationLevel.ERROR:
                urgency = "critical"
            elif level == NotificationLevel.WARNING:
                urgency = "normal"

            subprocess.Popen(["notify-send", title, message, "-u", urgency, "-t", str(self.config.notification_timeout)])
            return

        # 尝试 Python DBus
        try:
            from gi.repository import Notify  # type: ignore
            Notify.init("VibeNotification")
            n = Notify.Notification.new(title, message, None)
            n.set_timeout(self.config.notification_timeout)
            n.show()
        except Exception:
            pass

    def _notify_windows(self, title: str, message: str, level: NotificationLevel):
        """Windows 显示通知"""
        esc_title = escape_for_powershell(title)
        esc_message = escape_for_powershell(message)

        # 选择图标
        icon = "Information"
        if level == NotificationLevel.ERROR:
            icon = "Error"
        elif level == NotificationLevel.WARNING:
            icon = "Warning"
        elif level == NotificationLevel.SUCCESS:
            icon = "Information"

        ps_script = (
            "$title = '{t}'; $msg = '{m}'; "
            "[void][Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); "
            "[void][Reflection.Assembly]::LoadWithPartialName('System.Drawing'); "
            "$notify = New-Object System.Windows.Forms.NotifyIcon; "
            "$notify.Icon = [System.Drawing.SystemIcons]::{icon}; "
            "$notify.BalloonTipTitle = $title; "
            "$notify.BalloonTipText = $msg; "
            "$notify.Visible = $true; "
            "$notify.ShowBalloonTip({timeout}); "
            "Start-Sleep -Seconds 6; "
            "$notify.Dispose();"
        ).format(t=esc_title, m=esc_message, icon=icon, timeout=self.config.notification_timeout)

        subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_script])
