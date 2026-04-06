"""
共享 stdin 缓存

stdin 管道只能读取一次；本模块提供模块级缓存，
确保所有解析器共享同一份数据而不会因重复读取导致数据丢失。
"""

import json
import logging
import sys
from typing import Any, Dict, Optional

_UNREAD = object()
_cache: object = _UNREAD


def get_stdin_json() -> Optional[Dict[str, Any]]:
    """读取 stdin JSON（仅读取一次，后续调用返回缓存结果）。"""
    global _cache
    if _cache is not _UNREAD:
        return _cache if isinstance(_cache, dict) else None

    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read().strip()
            if raw:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    _cache = parsed
                    return _cache
    except Exception as exc:
        logging.getLogger(__name__).debug("读取 stdin JSON 失败: %s", exc)

    _cache = None
    return None
