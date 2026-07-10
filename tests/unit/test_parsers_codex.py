import json
import sys

import pytest

from vibe_notification.detectors.conversation import detect_conversation_end
from vibe_notification.parsers.codex import CodexParser


@pytest.fixture(autouse=True)
def _isolate_codex_turn_dedupe_state(monkeypatch, tmp_path):
    """测试中不要写入真实用户目录下的 Codex turn 去重状态。"""
    monkeypatch.setattr(
        "vibe_notification.parsers.codex.CODEX_TURN_DEDUPE_STATE_PATH",
        tmp_path / "codex-turn-dedupe.json",
        raising=False,
    )


def test_detect_conversation_end_ignores_assistant_message_event():
    """assistant-message 只是消息事件，不应直接视为本轮结束。"""
    event = {
        "type": "assistant-message",
        "agent": "codex",
        "message": "I am starting to work on this task.",
    }

    assert detect_conversation_end(event) is False


def test_detect_conversation_end_ignores_codex_user_prompt_submit_hook():
    """Codex 的 UserPromptSubmit hook 只是收到指令，不应通知。"""
    event = {
        "hook_event_name": "UserPromptSubmit",
        "cwd": "/tmp/project",
        "model": "gpt-5-codex",
        "permission_mode": "default",
        "prompt": "please fix this bug",
        "session_id": "session-1",
        "transcript_path": None,
    }

    assert detect_conversation_end(event) is False


def test_detect_conversation_end_ignores_codex_session_end_event():
    """SessionEnd/session-end 不是某次回复完成，不应触发通知。"""
    event = {
        "type": "session-end",
        "client": "codex-tui",
        "thread-id": "thread-1",
        "conversation_end": True,
    }

    assert detect_conversation_end(event) is False


def test_detect_conversation_end_ignores_nested_codex_session_end_event():
    """嵌套 session-end 即使带 conversation_end 标记也不应触发。"""
    event = {
        "client": "codex-tui",
        "thread-id": "thread-1",
        "data": {
            "type": "session-end",
            "conversation_end": True,
        },
    }

    assert detect_conversation_end(event) is False


def test_detect_conversation_end_ignores_codex_stop_hook_payload():
    """Codex Stop hook 输入不是 notify 事件，不应直接通知。"""
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

    assert detect_conversation_end(event) is False


def test_codex_parser_marks_official_agent_turn_complete_as_terminal(monkeypatch):
    """Codex 官方 legacy notify payload 应视为真实 turn 结束。"""
    event = {
        "type": "agent-turn-complete",
        "thread-id": "thread-1",
        "turn-id": "turn-1",
        "cwd": "/tmp/project",
        "client": "codex-tui",
        "input-messages": ["fix the tests"],
        "last-assistant-message": "Done and verified.",
    }
    monkeypatch.setattr(sys, "argv", ["python", "-m", "vibe_notification", json.dumps(event)])

    parser = CodexParser()
    parsed = parser.parse()

    assert parsed is not None
    assert parsed.type == "agent-turn-complete"
    assert parsed.message == "Done and verified."
    assert parsed.conversation_end is True
    assert parsed.is_last_turn is True


def test_codex_parser_suppresses_duplicate_notification_for_same_turn(monkeypatch):
    """同一 thread/turn 被新版 Codex 重放时，只能通知一次。"""
    event = {
        "type": "agent-turn-complete",
        "thread-id": "thread-1",
        "turn-id": "turn-1",
        "cwd": "/tmp/project",
        "client": "codex-tui",
        "input-messages": ["fix the tests"],
        "last-assistant-message": "Done and verified.",
    }
    argv = ["python", "-m", "vibe_notification", json.dumps(event)]

    monkeypatch.setattr(sys, "argv", argv)
    first = CodexParser().parse()
    monkeypatch.setattr(sys, "argv", argv)
    second = CodexParser().parse()

    assert first is not None
    assert first.conversation_end is True
    assert second is not None
    assert second.type == "turn-duplicate"
    assert second.conversation_end is False
    assert second.is_last_turn is False
    assert second.metadata.get("suppress_notification") is True


def test_codex_parser_allows_new_turn_in_same_thread(monkeypatch):
    """同一线程中的下一轮回复不能被 turn 去重误杀。"""
    base = {
        "type": "agent-turn-complete",
        "thread-id": "thread-1",
        "cwd": "/tmp/project",
        "client": "codex-tui",
        "input-messages": ["fix the tests"],
        "last-assistant-message": "Done and verified.",
    }
    first_event = {**base, "turn-id": "turn-1"}
    second_event = {**base, "turn-id": "turn-2"}

    monkeypatch.setattr(
        sys, "argv", ["python", "-m", "vibe_notification", json.dumps(first_event)]
    )
    first = CodexParser().parse()
    monkeypatch.setattr(
        sys, "argv", ["python", "-m", "vibe_notification", json.dumps(second_event)]
    )
    second = CodexParser().parse()

    assert first is not None
    assert first.conversation_end is True
    assert second is not None
    assert second.conversation_end is True


def test_detect_conversation_end_ignores_codex_subagent_turn_complete():
    """子代理 turn 完成不是主回复完成，不应触发用户通知。"""
    event = {
        "type": "agent-turn-complete",
        "thread-id": "thread-1",
        "turn-id": "turn-sub-1",
        "client": "codex-tui",
        "agent": "codex-subagent",
        "subagent_id": "sub-1",
        "last-assistant-message": "Done and verified.",
    }

    assert detect_conversation_end(event) is False


def test_codex_parser_marks_subagent_turn_complete_as_suppressed(monkeypatch):
    """Codex 子代理完成事件应被解析但显式标记为非终态。"""
    event = {
        "type": "agent-turn-complete",
        "thread-id": "thread-1",
        "turn-id": "turn-sub-1",
        "client": "codex-app-server",
        "agent": "task-agent",
        "sub_agent": {"id": "sub-1", "name": "code-reviewer"},
        "last-assistant-message": "Implemented the requested fix.",
    }
    monkeypatch.setattr(sys, "argv", ["python", "-m", "vibe_notification", json.dumps(event)])

    parsed = CodexParser().parse()

    assert parsed is not None
    assert parsed.conversation_end is False
    assert parsed.is_last_turn is False


def test_codex_parser_suppresses_official_subagent_stop_hook(monkeypatch):
    """官方 Codex SubagentStop hook 是子代理生命周期事件，应静默跳过。"""
    event = {
        "hook_event_name": "SubagentStop",
        "cwd": "/tmp/project",
        "model": "gpt-5-codex",
        "agent_id": "agent-1",
        "agent_type": "code-reviewer",
        "agent_transcript_path": "/tmp/subagent.jsonl",
        "session_id": "session-1",
    }
    monkeypatch.setattr(sys, "argv", ["python", "-m", "vibe_notification", json.dumps(event)])

    parsed = CodexParser().parse()

    assert parsed is not None
    assert parsed.type == "subagent-stop"
    assert parsed.agent == "codex-hook"
    assert parsed.conversation_end is False
    assert parsed.is_last_turn is False


def test_detect_conversation_end_ignores_codex_turn_complete_without_final_message():
    """缺少最终 assistant 文本时，不应仅凭 turn-complete 就通知。"""
    event = {
        "type": "agent-turn-complete",
        "thread-id": "thread-1",
        "turn-id": "turn-1",
        "client": "codex-tui",
        "input-messages": ["fix the tests"],
    }

    assert detect_conversation_end(event) is False


@pytest.mark.parametrize(
    "reply",
    ["OK", "No.", "Looks good.", "答案是 42。", "Working on it"],
)
def test_detect_conversation_end_accepts_official_codex_turn_complete_reply(reply):
    """官方 notify 已声明 turn 完成，不应再根据回复文案猜测。"""
    event = {
        "type": "agent-turn-complete",
        "thread-id": "thread-1",
        "turn-id": "turn-1",
        "client": "codex-tui",
        "input-messages": ["reply with exactly OK"],
        "last-assistant-message": reply,
    }

    assert detect_conversation_end(event) is True


def test_detect_conversation_end_accepts_codex_short_final_reply_with_explicit_flag():
    """若 provider 明确给出 final 标记，短回复也应视为终态。"""
    event = {
        "type": "agent-turn-complete",
        "thread-id": "thread-1",
        "turn-id": "turn-1",
        "client": "codex-tui",
        "input-messages": ["reply with exactly OK"],
        "last-assistant-message": "OK",
        "final": True,
    }

    assert detect_conversation_end(event) is True


def test_codex_parser_accepts_hook_payload_but_marks_it_non_terminal(monkeypatch):
    """误把 VibeNotification 接到 Codex hook 时，应静默跳过而不是误报。"""
    event = {
        "hook_event_name": "UserPromptSubmit",
        "cwd": "/tmp/project",
        "model": "gpt-5-codex",
        "permission_mode": "default",
        "prompt": "please fix this bug",
        "session_id": "session-1",
        "transcript_path": None,
    }
    monkeypatch.setattr(sys, "argv", ["python", "-m", "vibe_notification", json.dumps(event)])

    parser = CodexParser()

    assert parser.can_parse() is True

    parsed = parser.parse()

    assert parsed is not None
    assert parsed.type == "user-prompt-submit"
    assert parsed.message == "Codex 已接收用户指令"
    assert parsed.conversation_end is False
    assert parsed.is_last_turn is False
    assert parsed.metadata.get("suppress_notification") is True


def test_codex_parser_accepts_codex_stop_hook_payload_from_stdin(monkeypatch):
    """与 Claude 同名的 Codex Stop hook 也应由 CodexParser 识别并静默跳过。"""
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

    class _MockStdin:
        def isatty(self):
            return False

        def read(self):
            return json.dumps(event)

    monkeypatch.setattr(sys, "stdin", _MockStdin())

    import vibe_notification.parsers._stdin as _stdin_mod
    monkeypatch.setattr(_stdin_mod, "_cache", _stdin_mod._UNREAD)

    parser = CodexParser()

    assert parser.can_parse() is True

    parsed = parser.parse()

    assert parsed is not None
    assert parsed.type == "stop-hook"
    assert parsed.agent == "codex-hook"
    assert parsed.conversation_end is False
    assert parsed.is_last_turn is False


def test_detect_conversation_end_ignores_codex_app_server_non_terminal_turn_completed():
    """新版 app-server 的中间态 turn/completed 不应被当作最终结束。"""
    event = {
        "method": "turn/completed",
        "client": "codex-app-server",
        "data": {
            "turn": {
                "id": "turn-1",
                "status": "in_progress",
            },
            "item": {
                "agentMessage": {
                    "id": "msg-1",
                    "text": "I've received your instructions and will inspect the repository first.",
                    "phase": "commentary",
                }
            },
        },
    }

    assert detect_conversation_end(event) is False


def test_detect_conversation_end_ignores_completed_commentary_without_final_answer():
    """completed 状态若只携带 commentary，仍不是最终答复。"""
    event = {
        "method": "turn/completed",
        "client": "codex-app-server",
        "data": {
            "turn": {
                "id": "turn-1",
                "status": "completed",
            },
            "item": {
                "agentMessage": {
                    "id": "msg-1",
                    "text": "好的，我先检查仓库结构。",
                    "phase": "commentary",
                }
            },
        },
    }

    assert detect_conversation_end(event) is False


def test_codex_parser_marks_codex_app_server_terminal_turn_completed(monkeypatch):
    """新版 app-server 终态 turn/completed 应被识别为真实结束。"""
    event = {
        "method": "turn/completed",
        "client": "codex-app-server",
        "data": {
            "turn": {
                "id": "turn-1",
                "status": "completed",
            },
            "item": {
                "agentMessage": {
                    "id": "msg-1",
                    "text": "Finished the requested changes and verified the tests.",
                    "phase": "final_answer",
                }
            },
        },
    }
    monkeypatch.setattr(sys, "argv", ["python", "-m", "vibe_notification", json.dumps(event)])

    parser = CodexParser()
    parsed = parser.parse()

    assert parsed is not None
    assert parsed.type == "turn/completed"
    assert parsed.message == "Finished the requested changes and verified the tests."
    assert parsed.conversation_end is True
    assert parsed.is_last_turn is True


def test_detect_conversation_end_accepts_codex_app_server_short_final_reply():
    """结构化 final_answer/status 明确时，短回复也应视为终态。"""
    event = {
        "method": "turn/completed",
        "client": "codex-app-server",
        "data": {
            "turn": {
                "id": "turn-1",
                "status": "completed",
            },
            "item": {
                "agentMessage": {
                    "id": "msg-1",
                    "text": "OK",
                    "phase": "final_answer",
                }
            },
        },
    }

    assert detect_conversation_end(event) is True


def test_codex_parser_prefers_final_answer_over_commentary(monkeypatch):
    """同一 payload 同时有 commentary 和 final_answer 时，应优先取最终答复。"""
    event = {
        "method": "turn/completed",
        "client": "codex-app-server",
        "data": {
            "turn": {
                "id": "turn-1",
                "status": "completed",
            },
            "items": [
                {
                    "agentMessage": {
                        "id": "msg-1",
                        "text": "I'll inspect the repository first.",
                        "phase": "commentary",
                    }
                },
                {
                    "agentMessage": {
                        "id": "msg-2",
                        "text": "Implemented the fix and verified the workflow.",
                        "phase": "final_answer",
                    }
                },
            ],
        },
    }
    monkeypatch.setattr(sys, "argv", ["python", "-m", "vibe_notification", json.dumps(event)])

    parser = CodexParser()
    parsed = parser.parse()

    assert parsed is not None
    assert parsed.message == "Implemented the fix and verified the workflow."
    assert parsed.conversation_end is True


def test_codex_parser_captures_debug_payload_when_debug_enabled(monkeypatch, tmp_path, caplog):
    """DEBUG 模式下应记录原始 Codex payload，便于定位 provider 差异。"""
    event = {
        "type": "agent-turn-complete",
        "thread-id": "thread-1",
        "turn-id": "turn-1",
        "client": "codex-tui",
        "input-messages": ["fix the tests"],
        "last-assistant-message": "Done and verified.",
    }
    capture_path = tmp_path / "codex-events.jsonl"

    monkeypatch.setattr(sys, "argv", ["python", "-m", "vibe_notification", json.dumps(event)])
    monkeypatch.setattr(CodexParser, "DEBUG_CAPTURE_PATH", capture_path)
    caplog.set_level("DEBUG")

    parser = CodexParser()
    parsed = parser.parse()

    assert parsed is not None
    assert capture_path.exists() is True
    assert '"thread-id": "thread-1"' in capture_path.read_text(encoding="utf-8")
