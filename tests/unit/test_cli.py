from pathlib import Path

from vibe_notification.cli import parse_args, run_codex_wrapper
from vibe_notification.doctor import (
    _analyze_codex_config,
    format_doctor_report,
    run_doctor,
)
from vibe_notification.models import NotificationConfig


def test_parse_args_preserves_codex_args_for_wrapper():
    args, extra = parse_args(["--wrap-codex", "--", "-C", "/tmp/project", "fix tests"])

    assert args.wrap_codex is True
    assert extra == ["-C", "/tmp/project", "fix tests"]


def test_run_codex_wrapper_sends_session_end_notification(monkeypatch):
    captured = {}

    class DummyCompleted:
        returncode = 7

    class DummyNotifier:
        def __init__(self, config):
            captured["config"] = config

        def process_event(self, event):
            captured["event"] = event

    monkeypatch.setattr("vibe_notification.cli.shutil.which", lambda name: "/usr/local/bin/codex")
    monkeypatch.setattr("vibe_notification.cli.subprocess.run", lambda *args, **kwargs: DummyCompleted())
    monkeypatch.setattr("vibe_notification.cli.VibeNotifier", DummyNotifier)

    exit_code = run_codex_wrapper(
        NotificationConfig(),
        ["-C", "/tmp/project", "exec", "Reply with exactly OK."],
    )

    assert exit_code == 7
    assert captured["event"].type == "session-end"
    assert captured["event"].agent == "codex"
    assert captured["event"].conversation_end is True
    assert captured["event"].metadata["cwd"] == "/tmp/project"
    assert captured["event"].metadata["wrapped"] is True
    assert captured["event"].metadata["wrapped_args"] == [
        "-C",
        "/tmp/project",
        "exec",
        "Reply with exactly OK.",
    ]


def test_doctor_recommends_codex_stop_over_legacy_notify(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".codex").mkdir(parents=True)
    (home / ".config" / "vibe-notification").mkdir(parents=True)

    (home / ".claude" / "settings.json").write_text(
        '{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"python -m vibe_notification"}]}]}}',
        encoding="utf-8",
    )
    (home / ".codex" / "config.toml").write_text(
        'notify = ["python3", "-m", "vibe_notification"]\n',
        encoding="utf-8",
    )
    (home / ".config" / "vibe-notification" / "vibe_notification.log").write_text(
        "ok\n",
        encoding="utf-8",
    )
    (home / ".config" / "vibe-notification" / "config.json").write_text(
        '{"enable_notification": true, "enable_sound": true}',
        encoding="utf-8",
    )

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr("vibe_notification.doctor.platform.system", lambda: "Darwin")
    monkeypatch.setattr("vibe_notification.doctor.shutil.which", lambda cmd: "/opt/homebrew/bin/terminal-notifier" if cmd == "terminal-notifier" else None)

    report = format_doctor_report(run_doctor())

    assert "Claude Code 已配置 Stop hook" in report
    assert "Claude Code 未配置 SessionEnd hook（可选）" in report
    assert "无法区分过程消息与最终答复的旧版 notify 命令" in report
    assert "默认会静默跳过旧 notify" in report
    assert "VIBE_ALLOW_LEGACY_CODEX_NOTIFY=1" in report
    assert "VibeNotification 系统弹窗已启用" in report
    assert "检测到 terminal-notifier" in report
    assert "Claude Code 场景默认不绑定 sender" in report
    assert "无需配置 SessionEnd" in report


def test_doctor_warns_when_codex_stop_and_notify_are_both_configured(
    tmp_path, monkeypatch
):
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    (home / ".codex" / "config.toml").write_text(
        """
notify = ["python3", "-m", "vibe_notification"]

[[hooks.Stop]]
[[hooks.Stop.hooks]]
type = "command"
command = "python3 -m vibe_notification"
""",
        encoding="utf-8",
    )

    findings = list(_analyze_codex_config(home / ".codex" / "config.toml"))
    report = format_doctor_report(findings)

    assert "Codex 已配置 Stop hook" in report
    assert "同时配置了 Stop hook 和旧版 notify" in report
    assert "移除 notify" in report


def test_main_uses_env_config_override_for_notification_flag(monkeypatch, capsys):
    monkeypatch.setenv("VIBE_NOTIFICATION_NOTIFY", "0")
    monkeypatch.setattr("sys.argv", ["vibe_notification", "--test"])

    captured = {}

    class DummyNotifier:
        def __init__(self, config):
            captured["config"] = config

        def process_event(self, event):
            captured["event"] = event

    monkeypatch.setattr("vibe_notification.cli.VibeNotifier", DummyNotifier)

    from vibe_notification.cli import main

    main()

    assert captured["config"].enable_notification is False
    assert captured["event"].conversation_end is True
