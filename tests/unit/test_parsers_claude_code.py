import io
import json
import sys
from vibe_notification.parsers import ClaudeCodeParser


def test_session_end_event_triggers_notification(monkeypatch):
    """SessionEnd 钩子应触发会话结束通知"""
    monkeypatch.setenv("CLAUDE_HOOK_EVENT", "SessionEnd")
    parser = ClaudeCodeParser()

    assert parser.can_parse() is True
    event = parser.parse()

    assert event is not None
    assert event.agent == "claude-code"
    assert event.conversation_end is True
    assert event.is_last_turn is True
    assert event.metadata.get("event") == "SessionEnd"


def test_stdin_without_tool_name_still_detects_end(monkeypatch):
    """没有 toolName 的 stdin 事件也应检测会话结束"""
    data = {"finish_reason": "stop", "message": "done"}
    monkeypatch.delenv("CLAUDE_HOOK_EVENT", raising=False)
    parser = ClaudeCodeParser()

    # 模拟 stdin 数据并跳过 select.select
    monkeypatch.setattr(parser, "_stdin_has_data", lambda: True)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(data)))

    event = parser.parse()

    assert event is not None
    assert event.conversation_end is True
    assert event.tool_name is None
    assert event.agent == "claude-code"
