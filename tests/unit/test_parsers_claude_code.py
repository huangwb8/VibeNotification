import io
import json
import sys
from vibe_notification.parsers import ClaudeCodeParser
from vibe_notification.parsers._stdin import get_stdin_json


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
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(data)))

    # 重置 stdin 缓存以使用新的 mock stdin
    import vibe_notification.parsers._stdin as _stdin_mod
    monkeypatch.setattr(_stdin_mod, "_cache", _stdin_mod._UNREAD)

    parser = ClaudeCodeParser()

    # 通过共享缓存读取 stdin
    stdin_json = get_stdin_json()
    assert stdin_json == data

    event = parser.parse()

    assert event is not None
    assert event.conversation_end is True
    assert event.tool_name is None
    assert event.agent == "claude-code"


def test_claude_parser_ignores_codex_stop_hook_payload(monkeypatch):
    """Codex 的 Stop hook 负载不应被 Claude 解析器误认成 Claude Stop。"""
    data = {
        "hook_event_name": "Stop",
        "cwd": "/tmp/project",
        "model": "gpt-5-codex",
        "permission_mode": "default",
        "last_assistant_message": "Working on it",
        "session_id": "session-1",
        "stop_hook_active": False,
        "transcript_path": None,
    }
    monkeypatch.delenv("CLAUDE_HOOK_EVENT", raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(data)))

    import vibe_notification.parsers._stdin as _stdin_mod
    monkeypatch.setattr(_stdin_mod, "_cache", _stdin_mod._UNREAD)

    parser = ClaudeCodeParser()

    assert parser.can_parse() is False
