#!/usr/bin/env python3
"""
Run Codex normally and send a VibeNotification only after the Codex process exits.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    codex_path = shutil.which("codex")
    if not codex_path:
        print("未找到 codex 可执行文件，请先确认 Codex CLI 已安装到 PATH。", file=sys.stderr)
        return 127

    codex_args = [codex_path, *sys.argv[1:]]
    completed = subprocess.run(codex_args)

    event = {
        "type": "session-end",
        "agent": "codex",
        "message": "Codex 会话已结束",
        "summary": "Codex 会话已结束",
        "conversation_end": True,
        "is_last_turn": True,
        "cwd": str(Path.cwd()),
        "exit_code": completed.returncode,
    }

    notify_args = [sys.executable, "-m", "vibe_notification", json.dumps(event, ensure_ascii=False)]

    try:
        subprocess.run(notify_args, check=False)
    except Exception as exc:
        print(f"发送会话结束通知失败: {exc}", file=sys.stderr)

    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
