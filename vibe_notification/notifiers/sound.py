"""
声音通知器

负责播放通知声音
"""

from typing import Optional
from .base import BaseNotifier
from ..models import NotificationConfig, NotificationLevel
from ..adapters import PlatformAdapter


class SoundNotifier(BaseNotifier):
    """声音通知器"""

    def __init__(self, config: NotificationConfig, platform_adapter: PlatformAdapter):
        super().__init__(config)
        self.platform_adapter = platform_adapter

    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self.config.enable_sound and self.platform_adapter.is_sound_available()

    def notify(self, title: str, message: str, level: NotificationLevel = NotificationLevel.INFO, **kwargs):
        """播放通知声音"""
        if not self.is_enabled():
            return

        sound_type = kwargs.get("sound_type", self.config.sound_type)
        volume = kwargs.get("volume", self.config.sound_volume)
        self.log_notification(title, message, level)

        try:
            # 根据通知级别选择声音类型
            if level == NotificationLevel.SUCCESS:
                sound_type = "success"
            elif level == NotificationLevel.ERROR:
                sound_type = "error"

            # 使用平台适配器播放声音
            sound_file = kwargs.get("sound_file")
            self.platform_adapter.play_sound(sound_file, sound_type, volume)
        except Exception as e:
            self.logger.warning(f"播放声音失败: {e}")