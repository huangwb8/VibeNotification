# Notification Reliability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restore reliable macOS banner notifications and sound delivery for Claude Code / Codex CLI without regressing existing notification behavior.

**Architecture:** Fix the problem at two layers. First, make macOS sender attribution safer in terminal-hosted contexts so `terminal-notifier` is less likely to inherit a host app notification policy that suppresses banners. Second, relax Codex completion detection so concise but final replies still emit notifications while obvious progress chatter stays suppressed.

**Tech Stack:** Python, pytest, macOS `terminal-notifier` / `osascript`, Claude Code hooks, Codex notify integration

---

### Task 1: Model The Failures With Tests

**Files:**
- Modify: `tests/unit/test_adapters.py`
- Modify: `tests/unit/test_parsers_codex.py`
- Test: `tests/unit/test_adapters.py`
- Test: `tests/unit/test_parsers_codex.py`

**Step 1: Write the failing test**

Add tests for:
- macOS terminal / CLI host context defaults to no `-sender`
- Codex `agent-turn-complete` with a short final reply like `OK` is still terminal

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_adapters.py tests/unit/test_parsers_codex.py -q`
Expected: failures showing current sender strategy still binds host sender in terminal contexts and current conversation-end heuristics reject short final replies.

**Step 3: Write minimal implementation**

Update the macOS adapter host-context detection and Codex completion heuristics only as far as required by the new tests.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_adapters.py tests/unit/test_parsers_codex.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_adapters.py tests/unit/test_parsers_codex.py vibe_notification/adapters.py vibe_notification/detectors/conversation.py
git commit -m "fix: improve macos and codex notification reliability"
```

### Task 2: Harden Runtime Behavior

**Files:**
- Modify: `vibe_notification/adapters.py`
- Modify: `vibe_notification/detectors/conversation.py`
- Modify: `vibe_notification/doctor.py`

**Step 1: Write the failing test**

If needed, extend tests to cover:
- explicit `VIBE_NOTIFICATION_SENDER_MODE=auto|force` still restores sender
- doctor output still explains Claude `SessionEnd` / Codex `notify` semantics after the fix

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_cli.py tests/unit/test_adapters.py tests/unit/test_parsers_codex.py -q`
Expected: FAIL before implementation if new coverage was added.

**Step 3: Write minimal implementation**

Implement:
- terminal-hosted macOS context detection
- safer sender defaults in terminal / hook / wrapper contexts
- broader but still guarded Codex terminal-message acceptance
- any doctor wording needed for clarity

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_cli.py tests/unit/test_adapters.py tests/unit/test_parsers_codex.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add vibe_notification/adapters.py vibe_notification/detectors/conversation.py vibe_notification/doctor.py tests/unit/test_cli.py tests/unit/test_adapters.py tests/unit/test_parsers_codex.py
git commit -m "fix: stabilize cli notification delivery on macos"
```

### Task 3: Regression And Manual Verification

**Files:**
- Modify: `README.md`
- Modify: `README.zh.md`

**Step 1: Write the failing test**

No new automated test required if behavior is already covered; use manual verification checklist instead.

**Step 2: Run test to verify baseline**

Run: `python -m pytest tests/ -q`
Expected: all tests pass.

**Step 3: Write minimal implementation**

Document:
- macOS app notification style can still suppress banners
- Claude Code `SessionEnd` is required for session-exit notifications
- Codex `notify` is turn-based and `--wrap-codex` is session-exit-based

**Step 4: Run verification**

Run:
- `python -m vibe_notification --doctor`
- `python -m vibe_notification --test`
- `python -m pytest tests/ -q`

Expected:
- doctor reports accurate integration state
- test notification emits sound + macOS notification path successfully
- full test suite passes

**Step 5: Commit**

```bash
git add README.md README.zh.md docs/plans/2026-04-19-notification-reliability.md
git commit -m "docs: clarify macos and cli notification setup"
```
