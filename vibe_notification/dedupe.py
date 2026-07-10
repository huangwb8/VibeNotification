"""跨进程事件幂等工具。"""

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional


@contextmanager
def _state_lock(
    state_path: Path,
    timeout_seconds: float = 1.0,
    stale_seconds: float = 10.0,
) -> Iterator[bool]:
    """用可移植的独占 lock 文件保护状态读改写。"""
    lock_path = state_path.with_suffix(f"{state_path.suffix}.lock")
    deadline = time.monotonic() + timeout_seconds
    fd: Optional[int] = None

    while time.monotonic() < deadline:
        try:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("ascii", errors="ignore"))
            break
        except FileExistsError:
            try:
                if time.time() - lock_path.stat().st_mtime > stale_seconds:
                    lock_path.unlink(missing_ok=True)
                    continue
            except OSError:
                pass
            time.sleep(0.02)
        except OSError:
            break

    try:
        yield fd is not None
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass


def mark_recent_key(state_path: Path, key: str, ttl_seconds: float) -> bool:
    """原子记录短期事件 key；已存在返回 True，首次出现返回 False。

    锁不可用或状态写入失败时采用 fail-open，避免把真实回复永久误判为重复。
    """
    with _state_lock(state_path) as locked:
        if not locked:
            return False

        now = time.time()
        state: Dict[str, Any] = {"keys": {}}
        try:
            if state_path.exists():
                with state_path.open("r", encoding="utf-8") as fp:
                    loaded = json.load(fp)
                if isinstance(loaded, dict) and isinstance(loaded.get("keys"), dict):
                    state = loaded
        except (OSError, json.JSONDecodeError):
            pass

        keys: Dict[str, Any] = {}
        for stored_key, value in state.get("keys", {}).items():
            if isinstance(value, dict):
                expires_at = value.get("expires_at")
                if isinstance(expires_at, (int, float)) and float(expires_at) >= now:
                    keys[stored_key] = value
            elif isinstance(value, (int, float)):
                # 兼容 1.0.23/1.0.24 早期状态：旧格式只存 seen_at，无法恢复
                # 每个 key 的原始 TTL，因此按本次 TTL 做一次迁移性清理。
                if now - float(value) <= ttl_seconds:
                    keys[stored_key] = {
                        "seen_at": float(value),
                        "expires_at": float(value) + ttl_seconds,
                    }

        duplicate = key in keys
        keys[key] = {
            "seen_at": now,
            "expires_at": now + ttl_seconds,
        }

        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = state_path.with_name(f"{state_path.name}.{os.getpid()}.tmp")
            with tmp_path.open("w", encoding="utf-8") as fp:
                json.dump({"keys": keys}, fp, ensure_ascii=False)
            tmp_path.replace(state_path)
        except OSError:
            return False

        return duplicate
