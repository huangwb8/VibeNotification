"""
声音通知器

负责播放通知声音
"""

import subprocess
import os
from typing import Optional
from .base import BaseNotifier
from ..models import NotificationConfig, NotificationLevel
from ..utils import command_exists, detect_platform
from ..models import PlatformType


class SoundNotifier(BaseNotifier):
    """声音通知器"""

    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self.config.enable_sound

    def notify(self, title: str, message: str, level: NotificationLevel = NotificationLevel.INFO, **kwargs):
        """播放通知声音"""
        if not self.is_enabled():
            return

        sound_type = kwargs.get("sound_type", self.config.sound_type)
        self.log_notification(title, message, level)

        try:
            platform_type = detect_platform()
            if platform_type == PlatformType.MACOS:
                self._play_macos(sound_type)
            elif platform_type == PlatformType.LINUX:
                self._play_linux(sound_type)
            elif platform_type == PlatformType.WINDOWS:
                self._play_windows(sound_type)
        except Exception as e:
            self.logger.warning(f"播放声音失败: {e}")

    def _play_macos(self, sound_type: str):
        """macOS 播放声音"""
        if sound_type == "default":
            sound_path = "/System/Library/Sounds/Glass.aiff"
            if os.path.exists(sound_path) and command_exists("afplay"):
                subprocess.Popen(["afplay", sound_path])
                return

        if command_exists("say"):
            subprocess.Popen(["say", "会话完成"])

    def _play_linux(self, sound_type: str):
        """Linux 播放声音"""
        # 尝试播放系统声音
        if command_exists("paplay") and os.path.exists("/usr/share/sounds/freedesktop/stereo/complete.oga"):
            subprocess.Popen(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"])
            return

        # 尝试 TTS
        if command_exists("espeak"):
            subprocess.Popen(["espeak", "会话完成"])
        elif command_exists("spd-say"):
            subprocess.Popen(["spd-say", "会话完成"])

    def _play_windows(self, sound_type: str):
        """Windows 播放声音"""
        # 使用 PowerShell SAPI
        ps = 'Add-Type –AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak("会话完成");'
        subprocess.Popen(["powershell", "-NoProfile", "-Command", ps])