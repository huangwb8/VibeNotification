from unittest.mock import Mock
import io
import json
import sys

import pytest

from vibe_notification.core import VibeNotifier
from vibe_notification.models import NotificationConfig, NotificationEvent


@pytest.fixture(autouse=True)
def _isolate_codex_turn_dedupe_state(monkeypatch, tmp_path):
    """核心测试不读写真实用户的 Codex turn 幂等状态。"""
    monkeypatch.setattr(
        "vibe_notification.parsers.codex.CODEX_TURN_DEDUPE_STATE_PATH",
        tmp_path / "codex-turn-dedupe.json",
    )


def test_process_event_skips_non_terminal_event_when_detection_enabled():
    """默认只在会话结束时通知，中间事件应跳过。"""
    config = NotificationConfig(
        enable_sound=True,
        enable_notification=True,
        detect_conversation_end=True,
    )
    notifier = VibeNotifier(config)
    notifier.notification_builder = Mock(
        build_notification_content=Mock(
            return_value={
                "title": "Demo",
                "message": "Reply finished!",
                "level": "INFO",
                "subtitle": "IDE: Codex",
            }
        )
    )
    notifier.notifier_manager = Mock()

    event = NotificationEvent(
        type="assistant-message",
        agent="codex",
        message="working",
        summary="",
        timestamp="2026-03-21T00:00:00",
        conversation_end=False,
        is_last_turn=False,
    )

    notifier.process_event(event)

    notifier.notification_builder.build_notification_content.assert_not_called()
    notifier.notifier_manager.send_notifications.assert_not_called()


def test_process_event_allows_non_terminal_event_when_detection_disabled():
    """关闭结束检测后，允许按旧行为发送通知。"""
    config = NotificationConfig(
        enable_sound=True,
        enable_notification=True,
        detect_conversation_end=False,
    )
    notifier = VibeNotifier(config)
    notifier.notification_builder = Mock(
        build_notification_content=Mock(
            return_value={
                "title": "Demo",
                "message": "Reply finished!",
                "level": "INFO",
                "subtitle": "IDE: Codex",
            }
        )
    )
    notifier.notifier_manager = Mock()

    event = NotificationEvent(
        type="assistant-message",
        agent="codex",
        message="working",
        summary="",
        timestamp="2026-03-21T00:00:00",
        conversation_end=False,
        is_last_turn=False,
    )

    notifier.process_event(event)

    notifier.notification_builder.build_notification_content.assert_called_once_with(event)
    notifier.notifier_manager.send_notifications.assert_called_once()


def test_process_event_skips_explicitly_suppressed_event_when_detection_disabled():
    """明确标记为忽略的 hook 事件即使关闭结束检测也不应通知。"""
    config = NotificationConfig(
        enable_sound=True,
        enable_notification=True,
        detect_conversation_end=False,
    )
    notifier = VibeNotifier(config)
    notifier.notification_builder = Mock()
    notifier.notifier_manager = Mock()

    event = NotificationEvent(
        type="stop-duplicate",
        agent="claude-code",
        message="Claude 回复已处理",
        summary="Claude Code 重复 Stop（忽略通知）",
        timestamp="2026-03-21T00:00:00",
        conversation_end=False,
        is_last_turn=False,
        metadata={"suppress_notification": True},
    )

    notifier.process_event(event)

    notifier.notification_builder.build_notification_content.assert_not_called()
    notifier.notifier_manager.send_notifications.assert_not_called()


def test_run_notifies_for_codex_stop_hook_payload_from_stdin(monkeypatch):
    """Codex Stop 是主代理停止输出的精确通知时机。"""
    event = {
        "hook_event_name": "Stop",
        "cwd": "/tmp/project",
        "model": "gpt-5-codex",
        "permission_mode": "default",
        "last_assistant_message": "Implemented the fix and verified the tests.",
        "session_id": "session-1",
        "stop_hook_active": False,
        "transcript_path": None,
    }
    monkeypatch.setattr(sys, "argv", ["python", "-m", "vibe_notification"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))

    import vibe_notification.parsers._stdin as _stdin_mod
    monkeypatch.setattr(_stdin_mod, "_cache", _stdin_mod._UNREAD)

    notifier = VibeNotifier(
        NotificationConfig(
            enable_sound=True,
            enable_notification=True,
            detect_conversation_end=True,
        )
    )
    notifier.notification_builder = Mock(
        build_notification_content=Mock(
            return_value={
                "title": "Demo",
                "message": "Reply finished!",
                "level": "INFO",
                "subtitle": "IDE: Codex",
            }
        )
    )
    notifier.notifier_manager = Mock()

    notifier.run()

    notifier.notification_builder.build_notification_content.assert_called_once()
    notifier.notifier_manager.send_notifications.assert_called_once()


def test_run_never_notifies_for_codex_user_prompt_submit_when_detection_disabled(
    monkeypatch,
):
    """用户输入类 hook 必须强制静默，不受结束检测配置影响。"""
    event = {
        "hook_event_name": "UserPromptSubmit",
        "cwd": "/tmp/project",
        "model": "gpt-5-codex",
        "prompt": "new user input",
        "session_id": "session-1",
    }
    monkeypatch.setattr(
        sys, "argv", ["python", "-m", "vibe_notification", json.dumps(event)]
    )

    notifier = VibeNotifier(
        NotificationConfig(
            enable_sound=True,
            enable_notification=True,
            detect_conversation_end=False,
        )
    )
    notifier.notification_builder = Mock()
    notifier.notifier_manager = Mock()

    notifier.run()

    notifier.notification_builder.build_notification_content.assert_not_called()
    notifier.notifier_manager.send_notifications.assert_not_called()


def test_run_skips_unknown_event_instead_of_sending_test_notification():
    """协议新增事件未被识别时应 fail-closed，不能伪造成功通知。"""
    notifier = VibeNotifier(
        NotificationConfig(
            enable_sound=True,
            enable_notification=True,
            detect_conversation_end=False,
        )
    )
    notifier.parser_manager = Mock()
    notifier.parser_manager.get_available_parser.return_value = None
    notifier.notification_builder = Mock()
    notifier.notifier_manager = Mock()

    notifier.run()

    notifier.notification_builder.build_notification_content.assert_not_called()
    notifier.notifier_manager.send_notifications.assert_not_called()


def test_run_skips_unknown_claude_hook_even_with_terminal_payload(monkeypatch):
    """未来新增 hook 未适配前必须 fail-closed，不能落入通用终态解析。"""
    event = {
        "hook_event_name": "FutureHook",
        "conversation_end": True,
        "message": "future lifecycle event",
    }
    monkeypatch.setenv("CLAUDE_HOOK_EVENT", "FutureHook")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))

    import vibe_notification.parsers._stdin as _stdin_mod
    monkeypatch.setattr(_stdin_mod, "_cache", _stdin_mod._UNREAD)

    notifier = VibeNotifier(
        NotificationConfig(
            enable_sound=True,
            enable_notification=True,
            detect_conversation_end=False,
        )
    )
    notifier.notification_builder = Mock()
    notifier.notifier_manager = Mock()

    notifier.run()

    notifier.notification_builder.build_notification_content.assert_not_called()
    notifier.notifier_manager.send_notifications.assert_not_called()


def test_run_suppresses_ambiguous_legacy_codex_notify_by_default(
    monkeypatch, tmp_path
):
    """旧 notify 无法区分过程消息与最终答复，默认必须静默跳过。"""
    event = {
        "type": "agent-turn-complete",
        "thread-id": "thread-1",
        "turn-id": "turn-1",
        "cwd": "/tmp/project",
        "client": "codex-tui",
        "input-messages": ["please fix this bug"],
        "last-assistant-message": "Sure, I will inspect the repository first.",
    }
    monkeypatch.setattr(
        sys, "argv", ["python", "-m", "vibe_notification", json.dumps(event)]
    )

    notifier = VibeNotifier(
        NotificationConfig(
            enable_sound=True,
            enable_notification=True,
            detect_conversation_end=True,
        )
    )
    notifier.notification_builder = Mock(
        build_notification_content=Mock(
            return_value={
                "title": "Demo",
                "message": "Reply finished!",
                "level": "INFO",
                "subtitle": "IDE: Codex",
            }
        )
    )
    notifier.notifier_manager = Mock()

    monkeypatch.setattr("vibe_notification.debounce.SESSION_STATE_DIR", tmp_path)
    worker = Mock()
    monkeypatch.setattr("vibe_notification.debounce.spawn_debounce_worker", worker)

    notifier.run()

    worker.assert_not_called()
    notifier.notification_builder.build_notification_content.assert_not_called()
    notifier.notifier_manager.send_notifications.assert_not_called()


def test_run_allows_legacy_codex_notify_only_with_explicit_opt_in(
    monkeypatch, tmp_path
):
    """需要兼容旧 Codex 时，显式开关仍可恢复尾沿防抖。"""
    event = {
        "type": "agent-turn-complete",
        "thread-id": "thread-1",
        "turn-id": "turn-1",
        "cwd": "/tmp/project",
        "client": "codex-tui",
        "input-messages": ["please fix this bug"],
        "last-assistant-message": "Sure, I will inspect the repository first.",
    }
    monkeypatch.setattr(
        sys, "argv", ["python", "-m", "vibe_notification", json.dumps(event)]
    )
    monkeypatch.setenv("VIBE_ALLOW_LEGACY_CODEX_NOTIFY", "1")

    notifier = VibeNotifier(
        NotificationConfig(
            enable_sound=True,
            enable_notification=True,
            detect_conversation_end=True,
        )
    )
    notifier.notification_builder = Mock()
    notifier.notifier_manager = Mock()

    monkeypatch.setattr("vibe_notification.debounce.SESSION_STATE_DIR", tmp_path)
    worker = Mock(return_value=True)
    monkeypatch.setattr("vibe_notification.debounce.spawn_debounce_worker", worker)

    notifier.run()

    worker.assert_called_once()
    notifier.notification_builder.build_notification_content.assert_not_called()
    notifier.notifier_manager.send_notifications.assert_not_called()


def test_run_skips_claude_session_end_hook(monkeypatch):
    """Claude SessionEnd 不是回复完成，默认结束检测应跳过。"""
    monkeypatch.setenv("CLAUDE_HOOK_EVENT", "SessionEnd")

    notifier = VibeNotifier(
        NotificationConfig(
            enable_sound=True,
            enable_notification=True,
            detect_conversation_end=True,
        )
    )
    notifier.notification_builder = Mock(
        build_notification_content=Mock(
            return_value={
                "title": "Demo",
                "message": "Reply finished!",
                "level": "INFO",
                "subtitle": "IDE: Claude",
            }
        )
    )
    notifier.notifier_manager = Mock()

    notifier.run()

    notifier.notification_builder.build_notification_content.assert_not_called()
    notifier.notifier_manager.send_notifications.assert_not_called()


def test_run_skips_codex_completed_commentary_payload(monkeypatch, tmp_path):
    """Codex 接收消息后的 completed/commentary 事件不应触发提示音。"""
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
    monkeypatch.setattr(sys, "argv", ["python", "-m", "vibe_notification", json.dumps(event)])

    notifier = VibeNotifier(
        NotificationConfig(
            enable_sound=True,
            enable_notification=True,
            detect_conversation_end=True,
        )
    )
    notifier.notification_builder = Mock(
        build_notification_content=Mock(
            return_value={
                "title": "Demo",
                "message": "Reply finished!",
                "level": "INFO",
                "subtitle": "IDE: Codex",
            }
        )
    )
    notifier.notifier_manager = Mock()
    worker = Mock()
    monkeypatch.setattr("vibe_notification.debounce.SESSION_STATE_DIR", tmp_path)
    monkeypatch.setattr("vibe_notification.debounce.spawn_debounce_worker", worker)

    notifier.run()

    worker.assert_not_called()
    notifier.notification_builder.build_notification_content.assert_not_called()
    notifier.notifier_manager.send_notifications.assert_not_called()
