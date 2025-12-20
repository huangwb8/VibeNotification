#!/usr/bin/env python3
"""
国际化支持模块

提供中英双语支持
"""

import json
from typing import Dict, Any
from pathlib import Path

# 语言数据
TRANSLATIONS = {
    "zh": {
        "config_title": "=== VibeNotification 配置 ===",
        "current_config": "当前配置:",
        "sound_notification": "声音通知",
        "system_notification": "系统通知",
        "log_level": "日志级别",
        "notification_timeout": "通知超时",
        "sound_type": "声音类型",
        "sound_volume": "声音大小",
        "enable": "启用",
        "disable": "禁用",
        "modify_config": "是否修改配置？ (y/n): ",
        "enable_sound": "启用声音通知？ (y/n) [当前: {current}]: ",
        "enable_notification": "启用系统通知？ (y/n) [当前: {current}]: ",
        "set_log_level": "日志级别 (DEBUG/INFO/WARNING/ERROR) [当前: {current}]: ",
        "set_timeout": "通知超时时间 (毫秒) [当前: {current}]: ",
        "set_sound_type": "声音类型 (Glass/Ping/Pop/Tink/Basso) [当前: {current}]: ",
        "set_sound_volume": "声音大小 (0.0-1.0) [当前: {current}]: ",
        "config_saved": "配置已保存！",
        "config_cancelled": "配置已取消",
        "select_language": "请选择语言 / Please select language:",
        "chinese": "中文",
        "english": "English",
        "invalid_input": "输入无效，请重新输入",
        "press_esc_to_exit": "按 Esc 键退出配置",
        "press_enter_to_skip": "按 Enter 跳过此项"
    },
    "en": {
        "config_title": "=== VibeNotification Configuration ===",
        "current_config": "Current configuration:",
        "sound_notification": "Sound notification",
        "system_notification": "System notification",
        "log_level": "Log level",
        "notification_timeout": "Notification timeout",
        "sound_type": "Sound type",
        "sound_volume": "Sound volume",
        "enable": "Enabled",
        "disable": "Disabled",
        "modify_config": "Modify configuration? (y/n): ",
        "enable_sound": "Enable sound notification? (y/n) [current: {current}]: ",
        "enable_notification": "Enable system notification? (y/n) [current: {current}]: ",
        "set_log_level": "Log level (DEBUG/INFO/WARNING/ERROR) [current: {current}]: ",
        "set_timeout": "Notification timeout (ms) [current: {current}]: ",
        "set_sound_type": "Sound type (Glass/Ping/Pop/Tink/Basso) [current: {current}]: ",
        "set_sound_volume": "Sound volume (0.0-1.0) [current: {current}]: ",
        "config_saved": "Configuration saved!",
        "config_cancelled": "Configuration cancelled",
        "select_language": "请选择语言 / Please select language:",
        "chinese": "中文",
        "english": "English",
        "invalid_input": "Invalid input, please try again",
        "press_esc_to_exit": "Press Esc to exit configuration",
        "press_enter_to_skip": "Press Enter to skip"
    }
}

class I18n:
    """国际化支持类"""

    def __init__(self, language: str = "zh"):
        self.language = language
        self.translations = TRANSLATIONS.get(language, TRANSLATIONS["zh"])

    def t(self, key: str, **kwargs) -> str:
        """获取翻译文本"""
        text = self.translations.get(key, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass
        return text

    def set_language(self, language: str) -> None:
        """设置语言"""
        self.language = language
        self.translations = TRANSLATIONS.get(language, TRANSLATIONS["zh"])


# 全局 i18n 实例
_i18n_instance = None

def get_i18n() -> I18n:
    """获取全局 i18n 实例"""
    global _i18n_instance
    if _i18n_instance is None:
        _i18n_instance = I18n()
    return _i18n_instance

def set_language(language: str) -> None:
    """设置全局语言"""
    get_i18n().set_language(language)

def t(key: str, **kwargs) -> str:
    """获取翻译文本的快捷函数"""
    return get_i18n().t(key, **kwargs)