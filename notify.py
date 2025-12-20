#!/usr/bin/env python3
"""
VibeNotification 兼容性入口脚本

这个脚本提供了与原 notify.py 相同的接口，但使用新的 VibeNotification 引擎。
"""

import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vibe_notification import main

if __name__ == "__main__":
    main()