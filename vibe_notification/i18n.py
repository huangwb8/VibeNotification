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
        "sound_hint": "在终端中播放系统提示音；在安静环境可关闭",
        "system_hint": "发送系统通知弹窗；远程/无 GUI 环境可能无效",
        "log_level_hint": "DEBUG=最详细，INFO=常用，WARNING=仅警告，ERROR=仅错误",
        "timeout_hint": "通知停留毫秒数，过短可能看不到，过长可能打扰",
        "sound_type_hint": "可选 Glass/Ping/Pop/Tink/Basso，建议保持系统熟悉的提示音",
        "sound_volume_hint": "0.0-1.0，建议 0.2-0.8，避免过大音量",
        "current_project": "当前项目",
        "reply_finished": "回复结束啦！",
        "subtitle_ide": "IDE: {tool}",
        "error_title": "VibeNotification — 错误",
        "error_subtitle": "请检查配置或日志",
        "runtime_error": "运行时错误",
        "unknown_error": "未知错误",
        "test_message": "测试通知",
        "test_summary": "VibeNotification 测试运行",
        "enable": "启用",
        "disable": "禁用",
        "modify_config": "修改配置? (y/n): ",
        "enable_sound": "启用声音通知? (y/n) [{current}]: ",
        "enable_notification": "启用系统通知? (y/n) [{current}]: ",
        "set_log_level": "日志级别 [{current}]: ",
        "set_timeout": "通知超时(ms) [{current}]: ",
        "set_sound_type": "声音类型 [{current}]: ",
        "set_sound_volume": "声音大小(0.0-1.0) [{current}]: ",
        "config_saved": "配置已保存！",
        "config_cancelled": "配置已取消",
        "select_language": "选择语言 (1-中文 2-English):",
        "chinese": "中文",
        "english": "English",
        "invalid_input": "输入无效，请重试",
        "press_esc_to_exit": "Esc退出 | Enter跳过",
        "press_enter_to_skip": "Enter跳过此项"
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
        "sound_hint": "Play system sound in terminal; disable if you want silence",
        "system_hint": "Send system notification popup; may not work in headless/remote sessions",
        "log_level_hint": "DEBUG=most verbose, INFO=normal, WARNING=warnings only, ERROR=errors only",
        "timeout_hint": "Notification stay time (ms); too short may be missed, too long may annoy",
        "sound_type_hint": "Choose from Glass/Ping/Pop/Tink/Basso; keep a familiar system tone",
        "sound_volume_hint": "Range 0.0-1.0; 0.2-0.8 is usually comfortable",
        "current_project": "Current project",
        "reply_finished": "Reply finished!",
        "subtitle_ide": "IDE: {tool}",
        "error_title": "VibeNotification — Error",
        "error_subtitle": "Check configuration or logs",
        "runtime_error": "Runtime error",
        "unknown_error": "Unknown error",
        "test_message": "Test notification",
        "test_summary": "VibeNotification test run",
        "enable": "Enabled",
        "disable": "Disabled",
        "modify_config": "Modify config? (y/n): ",
        "enable_sound": "Enable sound? (y/n) [{current}]: ",
        "enable_notification": "Enable notification? (y/n) [{current}]: ",
        "set_log_level": "Log level [{current}]: ",
        "set_timeout": "Timeout(ms) [{current}]: ",
        "set_sound_type": "Sound type [{current}]: ",
        "set_sound_volume": "Volume(0.0-1.0) [{current}]: ",
        "config_saved": "Configuration saved!",
        "config_cancelled": "Configuration cancelled",
        "select_language": "Select language (1-中文 2-English):",
        "chinese": "中文",
        "english": "English",
        "invalid_input": "Invalid input, retry",
        "press_esc_to_exit": "Esc exit | Enter skip",
        "press_enter_to_skip": "Enter to skip"
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
