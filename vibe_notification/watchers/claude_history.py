"""
历史监听器

监听 ~/.claude/history.jsonl 中模型“本轮输出完成”的信号，并触发通知。
默认 agent 为 claude-code，可通过参数覆盖为 codex 等。
"""

import json
import time
from datetime import datetime
from pathlib import Path

from ..models import NotificationEvent
from ..detectors import detect_conversation_end
from ..utils import truncate_text


def watch_claude_history(
    notifier,
    history_path: Path | None = None,
    poll_interval: float = 2.0,
    agent_name: str = "claude-code",
) -> None:
    """监听 Claude Code/Codex 历史文件，一旦模型完成当前一轮输出就发送通知。"""
    history_path = history_path or (Path.home() / ".claude" / "history.jsonl")
    offset = 0

    notifier.logger.info(f"[{agent_name}] 监听历史文件: {history_path}")
    notifier.logger.info(f"[{agent_name}] 模型每轮输出结束即视为会话结束，发送通知")

    while True:
        try:
            if not history_path.exists():
                time.sleep(poll_interval)
                continue

            with history_path.open("r", encoding="utf-8") as f:
                f.seek(offset)
                lines = f.readlines()
                offset = f.tell()

            for line in lines:
                try:
                    event = json.loads(line)
                except Exception:
                    continue

                session_id = (event.get("sessionId") or "unknown").strip()
                display = (event.get("display") or "").strip()

                # 判断会话结束：模型完成当前一轮输出
                ended = detect_conversation_end(event)
                if ended:
                    notify_turn_complete(notifier, session_id, agent_name, display)
        except KeyboardInterrupt:
            notifier.logger.info(f"[{agent_name}] 已停止历史监听")
            return
        except Exception as e:
            notifier.logger.warning(f"[{agent_name}] 监听历史失败: {e}")

        time.sleep(poll_interval)


def notify_turn_complete(notifier, session_id: str, agent_name: str, display: str) -> None:
    """发送本轮会话结束通知。"""
    snippet = truncate_text(display, 120) if display else "模型输出已结束"
    event = NotificationEvent(
        type="conversation-complete",
        agent=agent_name,
        message=snippet,
        summary=f"{agent_name} 会话结束",
        timestamp=datetime.now().isoformat(),
        conversation_end=True,
        is_last_turn=True,
    )
    notifier.process_event(event)
