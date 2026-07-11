"""
Codex 会话防抖模块

通过延迟发送通知来解决 Codex notify 在每个 turn 都触发的问题：
每次收到 agent-turn-complete 事件时，写入会话状态文件并启动后台 worker；
worker 在冷却期结束后检查是否仍有新事件到来，只有「最后一个事件」才会真正发送通知。
"""

import json
import logging
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .models import NotificationEvent

logger = logging.getLogger(__name__)

# 默认静默期（秒）：Codex 的连续 turn 只在最后一次事件后通知。
DEFAULT_COOLDOWN_SECONDS = 10

# 会话状态目录
SESSION_STATE_DIR = Path.home() / ".config" / "vibe-notification" / "sessions"


def _cooldown_seconds() -> int:
    """读取静默期；非法配置安全回退到默认值。"""
    raw_value = os.environ.get("VIBE_DEBOUNCE_COOLDOWN")
    if raw_value is None:
        return DEFAULT_COOLDOWN_SECONDS
    try:
        return max(0, int(raw_value))
    except (TypeError, ValueError):
        logger.warning(
            "VIBE_DEBOUNCE_COOLDOWN=%r 无效，使用默认值 %d",
            raw_value,
            DEFAULT_COOLDOWN_SECONDS,
        )
        return DEFAULT_COOLDOWN_SECONDS


def _session_file_path(event_data: Dict[str, Any]) -> Optional[Path]:
    """根据事件数据确定会话状态文件路径。

    优先用 session_id，其次用 thread-id，最后用 cwd 做隔离。
    """
    session_id = event_data.get("session_id") or event_data.get("sessionId")
    thread_id = event_data.get("thread-id") or event_data.get("thread_id")
    cwd = event_data.get("cwd")

    identifier = session_id or thread_id or cwd or "default"
    # 文件名安全化
    safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in str(identifier))
    if not safe_name:
        safe_name = "default"
    return SESSION_STATE_DIR / f"{safe_name}.json"


def should_debounce(event: NotificationEvent) -> bool:
    """判断一个事件是否需要进入防抖流程。

    只有 Codex 的 turn-complete 类事件（且 conversation_end 由防抖逻辑判定）
    才需要防抖。其他事件（hook 事件、明确的 session-end 等）直接放行。
    """
    if not event.agent or "codex" not in event.agent.lower():
        return False

    cooldown = _cooldown_seconds()
    if cooldown <= 0:
        return False

    # session-end / hook 事件直接放行
    terminal_types = {"session-end", "session-start", "user-prompt-submit", "stop-hook"}
    if event.type in terminal_types:
        return False

    # turn-complete 类事件需要防抖
    turn_types = {
        "agent-turn-complete", "turn-completed",
        "turn-complete", "assistant-turn-complete",
    }
    return event.type in turn_types


def write_session_state(
    event_data: Dict[str, Any],
    event: NotificationEvent,
    generation: Optional[str] = None,
) -> Path:
    """将会话状态写入文件，供后台 worker 读取。"""
    state_path = _session_file_path(event_data)
    if state_path is None:
        state_path = SESSION_STATE_DIR / "default.json"

    state_path.parent.mkdir(parents=True, exist_ok=True)

    state = {
        "generation": generation or uuid.uuid4().hex,
        "updated_at": datetime.now().isoformat(),
        "event": event.to_dict(),
        "raw": event_data,
        "cooldown": _cooldown_seconds(),
    }

    tmp_path = state_path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as fp:
        json.dump(state, fp, ensure_ascii=False)
    tmp_path.replace(state_path)

    logger.debug("会话状态已写入: %s", state_path)
    return state_path


def spawn_debounce_worker(
    state_path: Path,
    cooldown: Optional[int] = None,
    generation: Optional[str] = None,
) -> bool:
    """以后台子进程方式启动 debounce worker。

    Worker 会等待 cooldown 秒，然后检查会话文件是否仍指向本次事件；
    如果是（说明没有更新的 turn 到来），就发送通知。
    """
    if cooldown is None:
        cooldown = _cooldown_seconds()

    if not generation:
        logger.warning("缺少防抖事件版本，跳过启动 worker")
        return False

    worker_script = Path(__file__).parent / "_debounce_worker.py"
    cmd = [
        sys.executable,
        str(worker_script),
        "--state-path", str(state_path),
        "--cooldown", str(cooldown),
        "--generation", generation,
    ]

    try:
        # 用 Popen 启动后台进程，不阻塞当前调用
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        logger.debug("已启动防抖 worker: cooldown=%ds, state=%s", cooldown, state_path)
        return True
    except Exception as exc:
        logger.warning("启动防抖 worker 失败，将直接发送通知: %s", exc)
        return False


def handle_codex_turn_event(event_data: Dict[str, Any], event: NotificationEvent) -> bool:
    """处理 Codex turn-complete 事件的防抖逻辑。

    返回 True 表示事件已被防抖接管（调用方不应立即发送通知）。
    返回 False 表示事件不需要防抖，调用方应立即处理。
    """
    if event.type == "stop-hook" and event.conversation_end:
        state_path = _session_file_path(event_data)
        if state_path is not None:
            state_path.unlink(missing_ok=True)
        return False

    if not should_debounce(event):
        return False

    cooldown = _cooldown_seconds()
    if cooldown <= 0:
        return False

    generation = uuid.uuid4().hex
    state_path = write_session_state(event_data, event, generation)
    return spawn_debounce_worker(state_path, cooldown, generation)
