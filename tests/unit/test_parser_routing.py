import io
import json
import sys

from vibe_notification.parsers.routing import detect_parser_type


def test_detect_parser_type_prefers_claude_env(monkeypatch):
    monkeypatch.setenv("CLAUDE_HOOK_EVENT", "Stop")

    assert detect_parser_type() == "claude_code"


def test_detect_parser_type_detects_codex_notify_from_argv(monkeypatch):
    event = {
        "type": "agent-turn-complete",
        "thread-id": "thread-1",
        "turn-id": "turn-1",
        "input-messages": ["fix tests"],
        "last-assistant-message": "Done",
    }
    monkeypatch.setattr(sys, "argv", ["python", "-m", "vibe_notification", json.dumps(event)])

    assert detect_parser_type() == "codex"


def test_detect_parser_type_detects_real_claude_stop_from_stdin(monkeypatch):
    event = {
        "hook_event_name": "Stop",
        "session_id": "session-1",
        "transcript_path": "/tmp/claude-transcript.jsonl",
        "cwd": "/tmp/project",
        "permission_mode": "default",
        "stop_hook_active": False,
    }
    monkeypatch.setattr(sys, "argv", ["python", "-m", "vibe_notification"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))

    import vibe_notification.parsers._stdin as _stdin_mod
    monkeypatch.setattr(_stdin_mod, "_cache", _stdin_mod._UNREAD)

    assert detect_parser_type() == "claude_code"


def test_detect_parser_type_detects_codex_stop_from_stdin(monkeypatch):
    event = {
        "hook_event_name": "Stop",
        "cwd": "/tmp/project",
        "model": "gpt-5-codex",
        "permission_mode": "default",
        "last_assistant_message": "Working on it",
        "session_id": "session-1",
        "stop_hook_active": False,
        "transcript_path": None,
    }
    monkeypatch.setattr(sys, "argv", ["python", "-m", "vibe_notification"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))

    import vibe_notification.parsers._stdin as _stdin_mod
    monkeypatch.setattr(_stdin_mod, "_cache", _stdin_mod._UNREAD)

    assert detect_parser_type() == "codex"
