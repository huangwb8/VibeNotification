import io
import json
import sys
from pathlib import Path

import pytest

from vibe_notification.parsers import ClaudeCodeParser
from vibe_notification.parsers._stdin import get_stdin_json


@pytest.fixture(autouse=True)
def _isolate_claude_stop_dedupe_state(monkeypatch, tmp_path):
    """测试中不要写入真实用户目录下的 Stop 去重状态。"""
    monkeypatch.setattr(
        "vibe_notification.parsers.claude_code.CLAUDE_STOP_DEDUPE_STATE_PATH",
        tmp_path / "claude-stop-dedupe.json",
    )


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


def test_notification_hook_is_not_reply_complete(monkeypatch):
    """Claude Notification hook 是提示/权限/空闲类事件，不是回复完成。"""
    data = {
        "hook_event_name": "Notification",
        "message": "Claude needs your permission",
        "notification_type": "permission_request",
    }
    monkeypatch.delenv("CLAUDE_HOOK_EVENT", raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(data)))
    _reset_stdin_cache()

    parser = ClaudeCodeParser()
    event = parser.parse()

    assert event is not None
    assert event.type == "notification"
    assert event.conversation_end is False
    assert event.metadata.get("suppress_notification") is True


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


def test_stop_prefers_official_last_message_over_stale_tool_transcript(
    monkeypatch,
    tmp_path,
):
    """新版 Stop 的最终文本优先于可能异步滞后的 transcript。"""
    transcript = tmp_path / "t.jsonl"
    _write_transcript(transcript, [
        _assistant_row([
            {"type": "tool_use", "name": "Read", "input": {}},
        ]),
    ])
    _feed_stop_stdin(monkeypatch, {
        "hook_event_name": "Stop",
        "session_id": "s1",
        "transcript_path": str(transcript),
        "stop_hook_active": False,
        "last_assistant_message": "最终回复已经完成。",
    })

    event = ClaudeCodeParser().parse()

    assert event is not None
    assert event.type == "agent-turn-complete"
    assert event.conversation_end is True


@pytest.mark.parametrize("pending_field", ["background_tasks", "session_crons"])
def test_stop_with_pending_background_work_is_suppressed(
    monkeypatch,
    pending_field,
):
    """后台任务仍会唤醒 turn 时，Stop 只是暂时空闲。"""
    _feed_stop_stdin(monkeypatch, {
        "hook_event_name": "Stop",
        "session_id": "s1",
        "stop_hook_active": False,
        "last_assistant_message": "当前阶段完成。",
        pending_field: [{"id": "pending-1"}],
    })

    event = ClaudeCodeParser().parse()

    assert event is not None
    assert event.type == "stop-intermediate"
    assert event.conversation_end is False
    assert event.metadata.get("suppress_notification") is True


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


def test_stop_with_transcript_showing_sidechain_assistant_is_skipped(monkeypatch, tmp_path):
    """Stop 指向子代理 sidechain 的最终文本时，不应当作主回复完成。"""
    transcript = tmp_path / "t.jsonl"
    sidechain = _assistant_row([{"type": "text", "text": "Subagent finished."}])
    sidechain["isSidechain"] = True
    _write_transcript(transcript, [sidechain])
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
    assert event.metadata.get("suppress_notification") is True


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


def test_duplicate_stop_for_same_transcript_reply_is_suppressed(monkeypatch, tmp_path):
    """同一条最终 assistant 回复触发多次 Stop 时，只第一次应通知。"""
    state_path = tmp_path / "claude-stop-dedupe.json"
    monkeypatch.setattr(
        "vibe_notification.parsers.claude_code.CLAUDE_STOP_DEDUPE_STATE_PATH",
        state_path,
        raising=False,
    )
    transcript = tmp_path / "t.jsonl"
    _write_transcript(transcript, [
        _assistant_row([{"type": "text", "text": "已完成。"}]),
    ])
    payload = {
        "hook_event_name": "Stop",
        "session_id": "s1",
        "transcript_path": str(transcript),
        "cwd": str(tmp_path),
        "stop_hook_active": False,
        "last_assistant_message": "已完成。",
    }

    _feed_stop_stdin(monkeypatch, payload)
    first = ClaudeCodeParser().parse()
    _feed_stop_stdin(monkeypatch, payload)
    second = ClaudeCodeParser().parse()

    assert first is not None
    assert first.conversation_end is True
    assert second is not None
    assert second.type == "stop-duplicate"
    assert second.conversation_end is False


def test_duplicate_stop_for_same_assistant_message_id_is_suppressed_when_transcript_grows(
    monkeypatch,
    tmp_path,
):
    """同一 Claude 消息的增量 transcript 快照只能通知一次。"""
    transcript = tmp_path / "t.jsonl"
    first_snapshot = _assistant_row([{"type": "text", "text": "已完成。"}])
    first_snapshot["message"]["id"] = "msg-1"
    second_snapshot = _assistant_row(
        [{"type": "text", "text": "已完成，测试通过。"}]
    )
    second_snapshot["message"]["id"] = "msg-1"
    payload = {
        "hook_event_name": "Stop",
        "session_id": "s1",
        "transcript_path": str(transcript),
        "cwd": str(tmp_path),
        "stop_hook_active": False,
    }

    _write_transcript(transcript, [first_snapshot])
    _feed_stop_stdin(monkeypatch, payload)
    first = ClaudeCodeParser().parse()

    _write_transcript(transcript, [first_snapshot, second_snapshot])
    _feed_stop_stdin(monkeypatch, payload)
    second = ClaudeCodeParser().parse()

    assert first is not None
    assert first.type == "agent-turn-complete"
    assert first.conversation_end is True
    assert second is not None
    assert second.type == "stop-duplicate"
    assert second.conversation_end is False
    assert second.is_last_turn is False
    assert second.metadata.get("suppress_notification") is True


def test_assistant_message_id_remains_deduplicated_after_short_fallback_ttl(
    monkeypatch,
    tmp_path,
):
    """稳定 message.id 使用长幂等窗口，超过文本兜底 60 秒仍不重放。"""
    transcript = tmp_path / "t.jsonl"
    snapshot = _assistant_row([{"type": "text", "text": "已完成。"}])
    snapshot["message"]["id"] = "msg-stable"
    _write_transcript(transcript, [snapshot])
    payload = {
        "hook_event_name": "Stop",
        "session_id": "s1",
        "transcript_path": str(transcript),
        "cwd": str(tmp_path),
        "stop_hook_active": False,
    }

    monkeypatch.setattr("vibe_notification.dedupe.time.time", lambda: 1_000.0)
    _feed_stop_stdin(monkeypatch, payload)
    first = ClaudeCodeParser().parse()

    monkeypatch.setattr("vibe_notification.dedupe.time.time", lambda: 1_061.0)
    _feed_stop_stdin(monkeypatch, payload)
    second = ClaudeCodeParser().parse()

    assert first is not None
    assert first.conversation_end is True
    assert second is not None
    assert second.type == "stop-duplicate"
    assert second.conversation_end is False


def test_stop_with_same_message_but_new_transcript_line_notifies(monkeypatch, tmp_path):
    """相同文本的新回复不应被误杀；transcript 行号变化代表新的一轮输出。"""
    state_path = tmp_path / "claude-stop-dedupe.json"
    monkeypatch.setattr(
        "vibe_notification.parsers.claude_code.CLAUDE_STOP_DEDUPE_STATE_PATH",
        state_path,
        raising=False,
    )
    transcript = tmp_path / "t.jsonl"
    payload = {
        "hook_event_name": "Stop",
        "session_id": "s1",
        "transcript_path": str(transcript),
        "cwd": str(tmp_path),
        "stop_hook_active": False,
        "last_assistant_message": "Done",
    }

    _write_transcript(transcript, [
        _assistant_row([{"type": "text", "text": "Done"}]),
    ])
    _feed_stop_stdin(monkeypatch, payload)
    first = ClaudeCodeParser().parse()

    _write_transcript(transcript, [
        _assistant_row([{"type": "text", "text": "Done"}]),
        {"type": "user", "message": {"role": "user", "content": "again"}},
        _assistant_row([{"type": "text", "text": "Done"}]),
    ])
    _feed_stop_stdin(monkeypatch, payload)
    second = ClaudeCodeParser().parse()

    assert first is not None
    assert first.conversation_end is True
    assert second is not None
    assert second.conversation_end is True


def test_duplicate_stop_without_transcript_uses_last_assistant_message(monkeypatch, tmp_path):
    """新版 Stop payload 提供 last_assistant_message；无 transcript 时也用它做短期去重。"""
    state_path = tmp_path / "claude-stop-dedupe.json"
    monkeypatch.setattr(
        "vibe_notification.parsers.claude_code.CLAUDE_STOP_DEDUPE_STATE_PATH",
        state_path,
        raising=False,
    )
    payload = {
        "hook_event_name": "Stop",
        "session_id": "s1",
        "cwd": str(tmp_path),
        "stop_hook_active": False,
        "last_assistant_message": "Finished one reply.",
    }

    _feed_stop_stdin(monkeypatch, payload)
    first = ClaudeCodeParser().parse()
    _feed_stop_stdin(monkeypatch, payload)
    second = ClaudeCodeParser().parse()

    assert first is not None
    assert first.conversation_end is True
    assert second is not None
    assert second.type == "stop-duplicate"
    assert second.conversation_end is False
