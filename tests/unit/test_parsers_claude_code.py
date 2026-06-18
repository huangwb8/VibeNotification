import io
import json
import sys
from pathlib import Path

from vibe_notification.parsers import ClaudeCodeParser
from vibe_notification.parsers._stdin import get_stdin_json


def _reset_stdin_cache():
    """重置共享 stdin 缓存，确保每次测试重新读取 mock stdin。"""
    import vibe_notification.parsers._stdin as _stdin_mod
    _stdin_mod._cache = _stdin_mod._UNREAD


def _write_transcript(path: Path, rows):
    """写入 transcript JSONL；rows 为 dict 列表。"""
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def _assistant_row(content_blocks):
    """构造一条 assistant 对话行。"""
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": content_blocks},
    }


def _feed_stop_stdin(monkeypatch, payload):
    """以 Stop 钩子 stdin 喂入解析器（不依赖环境变量）。"""
    monkeypatch.delenv("CLAUDE_HOOK_EVENT", raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    _reset_stdin_cache()


def test_session_end_event_is_not_reply_complete(monkeypatch):
    """SessionEnd 是会话生命周期事件，不应当作某次回复完成。"""
    monkeypatch.setenv("CLAUDE_HOOK_EVENT", "SessionEnd")
    parser = ClaudeCodeParser()

    assert parser.can_parse() is True
    event = parser.parse()

    assert event is not None
    assert event.agent == "claude-code"
    assert event.conversation_end is False
    assert event.is_last_turn is False
    assert event.metadata.get("event") == "SessionEnd"


def test_subagent_stop_event_is_not_main_reply_complete(monkeypatch):
    """SubagentStop 只代表子代理完成，不应触发主回复完成通知。"""
    monkeypatch.setenv("CLAUDE_HOOK_EVENT", "SubagentStop")
    parser = ClaudeCodeParser()

    assert parser.can_parse() is True
    event = parser.parse()

    assert event is not None
    assert event.agent == "claude-code-subagent"
    assert event.conversation_end is False
    assert event.is_last_turn is False
    assert event.metadata.get("event") == "SubagentStop"


def test_claude_stdin_session_end_is_not_reply_complete(monkeypatch):
    """非 hook 回退路径也不应把 session-end 当作回复完成。"""
    data = {
        "event": "session-end",
        "message": "Claude session ended",
        "conversation_end": True,
    }
    monkeypatch.delenv("CLAUDE_HOOK_EVENT", raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(data)))

    import vibe_notification.parsers._stdin as _stdin_mod
    monkeypatch.setattr(_stdin_mod, "_cache", _stdin_mod._UNREAD)

    parser = ClaudeCodeParser()
    event = parser.parse()

    assert event is not None
    assert event.type == "operation-complete"
    assert event.conversation_end is False
    assert event.is_last_turn is False


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


def test_claude_parser_accepts_real_claude_stop_hook_from_stdin(monkeypatch):
    """Claude 官方 stdin Stop hook 不应被误判成 Codex。"""
    data = {
        "hook_event_name": "Stop",
        "session_id": "session-1",
        "transcript_path": "/tmp/claude-transcript.jsonl",
        "cwd": "/tmp/project",
        "permission_mode": "default",
        "stop_hook_active": False,
    }
    monkeypatch.delenv("CLAUDE_HOOK_EVENT", raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(data)))

    import vibe_notification.parsers._stdin as _stdin_mod
    monkeypatch.setattr(_stdin_mod, "_cache", _stdin_mod._UNREAD)

    parser = ClaudeCodeParser()

    assert parser.can_parse() is True

    event = parser.parse()

    assert event is not None
    assert event.agent == "claude-code"
    assert event.conversation_end is True
    assert event.metadata.get("event") == "Stop"


def test_stop_with_transcript_showing_tool_use_is_intermediate(monkeypatch, tmp_path):
    """Stop 时 transcript 最后一条 assistant 仍在调用工具 → 中间停止，不应通知。

    Claude Code 新版在 agentic loop 中（调用工具/子代理）也会触发 Stop 钩子。
    此时 Claude 还会继续工作，不是真正的回复结束。
    """
    transcript = tmp_path / "t.jsonl"
    _write_transcript(transcript, [
        _assistant_row([{"type": "text", "text": "我来处理"}]),
        _assistant_row([{"type": "tool_use", "name": "Read", "input": {}}]),
    ])
    _feed_stop_stdin(monkeypatch, {
        "hook_event_name": "Stop",
        "session_id": "s1",
        "transcript_path": str(transcript),
        "cwd": str(tmp_path),
        "stop_hook_active": False,
    })

    event = ClaudeCodeParser().parse()

    assert event is not None
    assert event.conversation_end is False
    assert event.is_last_turn is False


def test_stop_with_transcript_showing_pure_text_notifies(monkeypatch, tmp_path):
    """Stop 时 transcript 最后一条 assistant 为纯文本（无 tool_use）→ 真正回复结束，应通知。"""
    transcript = tmp_path / "t.jsonl"
    _write_transcript(transcript, [
        _assistant_row([{"type": "tool_use", "name": "Read", "input": {}}]),
        {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result"}]}},
        _assistant_row([{"type": "text", "text": "已完成修复。"}]),
    ])
    _feed_stop_stdin(monkeypatch, {
        "hook_event_name": "Stop",
        "session_id": "s1",
        "transcript_path": str(transcript),
        "cwd": str(tmp_path),
        "stop_hook_active": False,
    })

    event = ClaudeCodeParser().parse()

    assert event is not None
    assert event.conversation_end is True
    assert event.is_last_turn is True


def test_stop_skips_metadata_lines_to_find_last_assistant(monkeypatch, tmp_path):
    """transcript 尾部混有 ai-title/attachment 等元数据行，应跳过找到真实 assistant。

    复现真实 transcript 结构：最后一条真实 assistant 是纯文本，应通知。
    """
    transcript = tmp_path / "t.jsonl"
    _write_transcript(transcript, [
        _assistant_row([{"type": "text", "text": "真正的最终回复"}]),
        {"type": "attachment", "attachment": {"kind": "foo"}},
        {"type": "ai-title", "aiTitle": "标题"},
        {"type": "last-prompt", "prompt": "..."},
    ])
    _feed_stop_stdin(monkeypatch, {
        "hook_event_name": "Stop",
        "transcript_path": str(transcript),
        "stop_hook_active": False,
    })

    event = ClaudeCodeParser().parse()

    assert event is not None
    assert event.conversation_end is True


def test_stop_skips_metadata_then_finds_tool_use_is_intermediate(monkeypatch, tmp_path):
    """transcript 尾部元数据行之后，最后真实 assistant 含 tool_use → 中间停止。

    复现真实结构：尾部是元数据 + 正在调用工具的 assistant，应跳过通知。
    """
    transcript = tmp_path / "t.jsonl"
    _write_transcript(transcript, [
        _assistant_row([
            {"type": "text", "text": "现在读取文件"},
            {"type": "tool_use", "name": "Read", "input": {}},
        ]),
        {"type": "ai-title", "aiTitle": "标题"},
        {"type": "attachment", "attachment": {"kind": "foo"}},
    ])
    _feed_stop_stdin(monkeypatch, {
        "hook_event_name": "Stop",
        "transcript_path": str(transcript),
        "stop_hook_active": False,
    })

    event = ClaudeCodeParser().parse()

    assert event is not None
    assert event.conversation_end is False


def test_stop_with_stop_hook_active_is_skipped(monkeypatch, tmp_path):
    """stop_hook_active=True 表示 Stop 链重复触发（上次 Stop 导致 Claude 继续），跳过避免重复通知。"""
    transcript = tmp_path / "t.jsonl"
    _write_transcript(transcript, [
        _assistant_row([{"type": "text", "text": "done"}]),
    ])
    _feed_stop_stdin(monkeypatch, {
        "hook_event_name": "Stop",
        "transcript_path": str(transcript),
        "stop_hook_active": True,
    })

    event = ClaudeCodeParser().parse()

    assert event is not None
    assert event.conversation_end is False


def test_stop_without_transcript_path_falls_back_to_notify(monkeypatch):
    """无 transcript_path 时，保守通知（保持原有行为，避免漏报）。"""
    _feed_stop_stdin(monkeypatch, {
        "hook_event_name": "Stop",
        "session_id": "s1",
        "stop_hook_active": False,
    })

    event = ClaudeCodeParser().parse()

    assert event is not None
    assert event.conversation_end is True


def test_stop_with_missing_transcript_file_falls_back_to_notify(monkeypatch, tmp_path):
    """transcript_path 指向不存在的文件，保守通知（回退，不漏报）。"""
    _feed_stop_stdin(monkeypatch, {
        "hook_event_name": "Stop",
        "transcript_path": str(tmp_path / "nonexistent.jsonl"),
        "stop_hook_active": False,
    })

    event = ClaudeCodeParser().parse()

    assert event is not None
    assert event.conversation_end is True
