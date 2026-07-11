#!/usr/bin/env python3
"""
Codex 防抖后台 Worker

由 debounce.py 以子进程方式启动。等待冷却期结束后，
检查会话状态文件是否仍指向本次事件；若是，则发送通知。
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# 将项目根目录加入 sys.path 以便导入 vibe_notification
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from vibe_notification.models import NotificationEvent
from vibe_notification.core import VibeNotifier


def claim_session_event(
    state_path: Path, generation: str
) -> Optional[Dict[str, Any]]:
    """仅由最新一代 worker 原子消费状态，旧 worker 保持静默。"""
    if not state_path.exists():
        return None

    try:
        with state_path.open("r", encoding="utf-8") as fp:
            state = json.load(fp)
    except (json.JSONDecodeError, OSError):
        return None

    if state.get("generation") != generation:
        return None

    claim_path = state_path.with_name(f".{state_path.name}.{generation}.claim")
    try:
        state_path.replace(claim_path)
    except OSError:
        return None

    try:
        with claim_path.open("r", encoding="utf-8") as fp:
            claimed_state = json.load(fp)
    except (json.JSONDecodeError, OSError):
        claim_path.unlink(missing_ok=True)
        return None

    if claimed_state.get("generation") != generation:
        if not state_path.exists():
            claim_path.replace(state_path)
        else:
            claim_path.unlink(missing_ok=True)
        return None

    claim_path.unlink(missing_ok=True)
    event_dict = claimed_state.get("event")
    return event_dict if isinstance(event_dict, dict) else None


def main() -> int:
    parser = argparse.ArgumentParser(description="VibeNotification debounce worker")
    parser.add_argument("--state-path", required=True, help="会话状态文件路径")
    parser.add_argument("--cooldown", required=True, type=int, help="冷却期（秒）")
    parser.add_argument("--generation", required=True, help="事件版本标识")
    args = parser.parse_args()

    state_path = Path(args.state_path)
    cooldown = args.cooldown

    # 等待冷却期
    time.sleep(cooldown)

    event_dict = claim_session_event(state_path, args.generation)
    if not event_dict:
        return 0

    # 如果状态文件仍然存在且未被替换，说明这是最后一个事件，发送通知
    # 但标记 conversation_end 为 True，因为这是「确认的最终 turn」
    event_dict["conversation_end"] = True
    event_dict["is_last_turn"] = True

    try:
        event = NotificationEvent.from_dict(event_dict)
    except Exception:
        return 1

    try:
        notifier = VibeNotifier()
        notifier.process_event(event)
    except Exception as exc:
        # worker 在后台运行，只能写日志
        logging.basicConfig(
            filename=str(
                Path.home() / ".config" / "vibe-notification" / "debounce-worker.log"
            ),
            level=logging.DEBUG,
        )
        logging.getLogger(__name__).error("Worker 发送通知失败: %s", exc, exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
