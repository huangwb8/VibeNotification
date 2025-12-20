#!/usr/bin/env python3
"""
VibeNotification 兼容性入口脚本

这个脚本提供了与原 notify.py 相同的接口，但使用新的包结构。
"""

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vibe_notification.cli import main

if __name__ == "__main__":
    main()