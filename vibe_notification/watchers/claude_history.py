"""
历史监听器

监听 ~/.claude/history.jsonl 中模型“本轮输出完成”的信号，并触发通知。
默认 agent 为 claude-code，可通过参数覆盖。
"""

import json
import time
from datetime import datetime
from pathlib import Path

from ..models import NotificationEvent
from ..detectors import detect_conversation_end
from ..utils import truncate_text


def watch_claude_history_smart(
    notifier,
    history_path: Path | None = None,
    poll_interval: float = 2.0,
    agent_name: str = "claude-code",
) -> None:
    """监听 Claude Code 历史文件，一旦模型完成当前一轮输出就发送通知。"""
    history_path = history_path or (Path.home() / ".claude" / "history.jsonl")
    offset = 0
    last_session_id = None
    last_event_user = False  # 跟踪上一个事件是否是用户输入

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
                timestamp = event.get("timestamp", 0)

                # 判断是否是用户输入
                # 通常用户输入比较简短，且不包含解释性内容
                is_user_input = is_likely_user_input(display, event)

                # 如果是新的会话，重置状态
                if session_id != last_session_id:
                    last_session_id = session_id
                    last_event_user = False
                    continue

                # 检测模式：用户输入 -> 助手输出
                if not is_user_input and last_event_user and display:
                    # 这看起来像是助手对用户输入的回应
                    # 等待一小段时间确保输出完整
                    time.sleep(0.5)

                    # 检查是否有后续的同一会话事件
                    if not has_subsequent_events(history_path, timestamp, session_id, offset):
                        # 没有后续事件，说明输出可能已完成
                        notify_turn_complete(notifier, session_id, agent_name, display)

                # 更新状态
                last_event_user = is_user_input

        except KeyboardInterrupt:
            notifier.logger.info(f"[{agent_name}] 已停止历史监听")
            return
        except Exception as e:
            notifier.logger.warning(f"[{agent_name}] 监听历史失败: {e}")

        time.sleep(poll_interval)


def watch_claude_history(
    notifier,
    history_path: Path | None = None,
    poll_interval: float = 2.0,
    agent_name: str = "claude-code",
) -> None:
    """原始的简单监听模式，使用通用的对话结束检测。"""
    from pathlib import Path
    history_path = history_path or (Path.home() / ".claude" / "history.jsonl")
    offset = 0

    notifier.logger.info(f"[{agent_name}] 监听历史文件: {history_path}")
    notifier.logger.info(f"[{agent_name}] 使用通用检测模式")

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

                # 使用通用检测逻辑
                ended = detect_conversation_end(event)
                if ended:
                    notify_turn_complete(notifier, session_id, agent_name, display)

        except KeyboardInterrupt:
            notifier.logger.info(f"[{agent_name}] 已停止历史监听")
            return
        except Exception as e:
            notifier.logger.warning(f"[{agent_name}] 监听历史失败: {e}")

        time.sleep(poll_interval)


def is_likely_user_input(display: str, event: dict) -> bool:
    """判断是否是用户输入"""
    if not display:
        return False

    # 用户输入通常比较简短
    if len(display) < 50:
        # 检查是否包含命令或问题的特征
        question_words = ["吗", "？", "?", "如何", "怎么", "什么", "为什么", "哪里", "帮我", "请", "能否"]
        if any(word in display for word in question_words):
            return True

    # 检查是否有常见的用户输入模式
    user_patterns = [
        "帮我", "请", "能否", "可不可以", "如何", "怎么", "什么", "为什么",
        "查看", "显示", "列出", "搜索", "找到", "打开", "关闭", "启动", "停止"
    ]

    if any(pattern in display for pattern in user_patterns):
        return True

    # 检查是否是单行命令或简短请求
    lines = display.strip().split('\n')
    if len(lines) == 1 and len(display) < 100:
        return True

    # 默认认为是助手输出
    return False


def has_subsequent_events(history_path: Path, current_timestamp: int, session_id: str, current_offset: int) -> bool:
    """检查在当前时间戳之后是否有同一会话的后续事件"""
    try:
        # 读取文件的最后部分来检查
        with history_path.open("r", encoding="utf-8") as f:
            f.seek(current_offset)
            lines = f.readlines()

            # 检查后续几行是否有同一会话的事件
            for line in lines[-5:]:  # 只检查最后5行
                try:
                    event = json.loads(line.strip())
                    if (event.get("sessionId") == session_id and
                        event.get("timestamp", 0) > current_timestamp):
                        return True
                except:
                    continue

    except Exception:
        pass

    return False


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
