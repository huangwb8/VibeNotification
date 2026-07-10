import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from vibe_notification.dedupe import mark_recent_key


def test_mark_recent_key_is_atomic_across_concurrent_callers(tmp_path):
    """并发重复事件必须恰好只有一个调用方获得首次处理权。"""
    state_path = tmp_path / "dedupe.json"

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(
            executor.map(
                lambda _: mark_recent_key(state_path, "same-turn", 60),
                range(16),
            )
        )

    assert results.count(False) == 1
    assert results.count(True) == 15


def test_mark_recent_key_keeps_distinct_events_independent(tmp_path):
    state_path = tmp_path / "dedupe.json"

    assert mark_recent_key(state_path, "turn-1", 60) is False
    assert mark_recent_key(state_path, "turn-2", 60) is False


def test_short_ttl_event_does_not_expire_existing_long_ttl_key(monkeypatch, tmp_path):
    """每个 key 必须保留自己的 TTL，短期兜底不能清除稳定身份。"""
    state_path = tmp_path / "mixed-ttl.json"

    monkeypatch.setattr("vibe_notification.dedupe.time.time", lambda: 1_000.0)
    assert mark_recent_key(state_path, "stable-id", 86_400) is False

    monkeypatch.setattr("vibe_notification.dedupe.time.time", lambda: 1_061.0)
    assert mark_recent_key(state_path, "fallback-text", 60) is False

    monkeypatch.setattr("vibe_notification.dedupe.time.time", lambda: 1_062.0)
    assert mark_recent_key(state_path, "stable-id", 86_400) is True


def test_mark_recent_key_is_atomic_across_processes(tmp_path):
    """真实独立进程竞争同一 key 时，也必须只有一个首次处理者。"""
    state_path = tmp_path / "process-dedupe.json"
    script = (
        "import sys; "
        "from pathlib import Path; "
        "from vibe_notification.dedupe import mark_recent_key; "
        "print(int(mark_recent_key(Path(sys.argv[1]), 'same-turn', 60)))"
    )
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", script, str(state_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(8)
    ]
    completed = [process.communicate(timeout=10) for process in processes]

    assert all(process.returncode == 0 for process in processes)
    results = [int(stdout.strip()) for stdout, _ in completed]
    assert results.count(0) == 1
    assert results.count(1) == 7
