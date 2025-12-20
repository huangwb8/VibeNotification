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
            # 提示配置禁用了系统通知，避免用户误以为失败
            self.logger.info("系统通知已禁用（enable_notification = False）")
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
            try:
                args = [
                    "terminal-notifier",
                    "-title",
                    title,
                    "-message",
                    message,
                    "-sound", "default"  # 添加声音提示
                ]
                if subtitle:
                    args.extend(["-subtitle", subtitle])
                # 同步等待可捕获失败信息，便于诊断；失败则回退
                self.logger.info(f"发送 terminal-notifier 通知: {' '.join(args)}")
                result = subprocess.run(args, check=True, capture_output=True, text=True)
                self.logger.info(f"terminal-notifier 成功: stdout={result.stdout}, stderr={result.stderr}")
                return
            except Exception as e:
                self.logger.warning(f"terminal-notifier 通知失败，回退到 osascript: {e}")

        # 先尝试原文 osascript
        try:
            esc_msg = escape_for_osascript(message)
            esc_title = escape_for_osascript(title)
            esc_sub = escape_for_osascript(subtitle)

            script = f'display notification "{esc_msg}" with title "{esc_title}"'
            if esc_sub:
                script += f' subtitle "{esc_sub}"'
            script += ' sound name "default"'  # 添加声音
            self.logger.info(f"发送 osascript 通知: {script}")
            result = subprocess.run(["osascript", "-e", script], check=True, capture_output=True, text=True)
            self.logger.info(f"osascript 成功: stdout={result.stdout}, stderr={result.stderr}")
            return
        except Exception as e:
            self.logger.warning(f"osascript 通知失败，尝试降级: {e}")

        # 尝试 System Events 版本（某些环境对 display notification 有差异）
        try:
            esc_msg = escape_for_osascript(message)
            esc_title = escape_for_osascript(title)
            esc_sub = escape_for_osascript(subtitle)
            script = f'tell application "System Events" to display notification "{esc_msg}" with title "{esc_title}"'
            if esc_sub:
                script += f' subtitle "{esc_sub}"'
            subprocess.run(["osascript", "-e", script], check=True)
            return
        except Exception as e:
            self.logger.warning(f"System Events 通知失败，尝试 ASCII 降级: {e}")

        # 再尝试降级：移除非 ASCII 以规避个别 AppleScript 解析问题
        try:
            def to_ascii_safe(s: str) -> str:
                return s.encode("ascii", errors="ignore").decode() or "Notification"

            esc_msg = escape_for_osascript(to_ascii_safe(message))
            esc_title = escape_for_osascript(to_ascii_safe(title))
            esc_sub = escape_for_osascript(to_ascii_safe(subtitle))

            script = f'display notification "{esc_msg}" with title "{esc_title}"'
            if esc_sub:
                script += f' subtitle "{esc_sub}"'
            subprocess.run(["osascript", "-e", script], check=True)
            return
        except Exception as e:
            self.logger.warning(f"降级 osascript 仍失败: {e}")
            raise

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
