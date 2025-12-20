#!/bin/bash
# 测试 Codex notify 是否被调用

echo "$(date): Codex notify 被调用" >> /tmp/codex_notify_test.log
echo "参数: $@" >> /tmp/codex_notify_test.log
echo "---" >> /tmp/codex_notify_test.log

# 调用实际的通知系统
python3 -m vibe_notification "$@"
