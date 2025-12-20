"""
检测器模块

包含各种检测器的实现
"""

from .conversation import detect_conversation_end, detect_conversation_end_from_hook

__all__ = ["detect_conversation_end", "detect_conversation_end_from_hook"]