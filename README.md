<div align="center">

# VibeNotification

[![PyPI](https://img.shields.io/pypi/v/vibe-notification.svg)](https://pypi.org/project/vibe-notification/)
[![Python](https://img.shields.io/pypi/pyversions/vibe-notification.svg)](https://pypi.org/project/vibe-notification/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)](#installation)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

English | [中文](README.zh.md)

<strong> Stop waiting when vibe coding — Give a notification when Claude Code or Codex finishes replies — </strong>

[Blog walkthrough (Chinese): AI应用系列 一个简单的Vibe coding的通知系统](https://blognas.hwb0307.com/ai/6659)

</div>

![image-20251221214216954](https://chevereto.hwb0307.com/images/2025/12/21/image-20251221214216954.png)

## Installation

- Stable (PyPI): `pip install vibe-notification`
- Dev: `pip install -e .`
- Optional venv: `python -m venv venv && source venv/bin/activate`
- Verify: `python -m vibe_notification --test` (should toast and chime when enabled)
- Interactive setup: `python -m vibe_notification --config`
  - Default config file: `~/.config/vibe-notification/config.json`
  - Make sure both sound and system notifications are enabled

## Quick Start

### Claude Code

- Recommended hook: `Stop` (when each main reply completes).
- If what you want is "notify me when this reply is done", use `Stop`. That is the default and the only recommended hook.
- Do not attach the notifier command to `SessionEnd` or `SubagentStop`: VibeNotification ignores them by default to avoid duplicate alerts from session-exit, subagent, or tool-chain lifecycle events.
- On macOS, VibeNotification now defaults to `sender` off in Claude Code hook contexts and terminal-hosted CLI contexts for more reliable banners. If you explicitly want host-app attribution/icon, set `VIBE_NOTIFICATION_SENDER_MODE=force`.
- If a notification appears only in Notification Center, check `System Settings > Notifications` for the effective app (`terminal-notifier` when sender is off, or the host app such as VS Code / Terminal when sender is auto/force). Make sure notifications are allowed, banner/alert style is enabled, and Focus is not suppressing them.
- Edit `~/.claude/settings.json` and add a Stop hook:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "env VIBE_NOTIFICATION_SENDER_MODE=off python -m vibe_notification"
          }
        ]
      }
    ]
  }
}
```

- Example full settings snippet with environment variables:

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "xxx",
    "ANTHROPIC_BASE_URL": "https://open.bigmodel.cn/api/anthropic",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-4.6",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-4.6",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-4.6",
    "ANTHROPIC_MODEL": "glm-4.6",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "DISABLE_ERROR_REPORTING": "1",
    "DISABLE_TELEMETRY": "1",
    "MCP_TIMEOUT": "60000"
  },
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "command": "env VIBE_NOTIFICATION_SENDER_MODE=off python -m vibe_notification",
            "type": "command"
          }
        ]
      }
    ]
  },
  "includeCoAuthoredBy": false,
  "outputStyle": "engineer-professional"
}
```

### Codex CLI

Use a `Stop` hook in `~/.codex/config.toml`. It runs when the main agent stops the current turn after its tool calls and multi-step work; receiving a user message, a subagent stopping, or the whole session exiting does not count as task completion:

```toml
[[hooks.Stop]]

[[hooks.Stop.hooks]]
type = "command"
command = "python3 -m vibe_notification"
timeout = 30
```

Do not configure this `Stop` hook and the legacy `notify` command at the same time, because the same task can arrive through both event channels. Legacy `agent-turn-complete` payloads do not include the `commentary` / `final_answer` phase, so no fixed quiet period can reliably identify the final reply. VibeNotification therefore suppresses legacy `notify` events by default. Only when an older Codex version cannot use hooks, set `VIBE_ALLOW_LEGACY_CODEX_NOTIFY=1` to restore the 10-second trailing-edge compatibility debounce; long tool calls can still make that mode misclassify an intermediate turn as complete. Use `VIBE_DEBOUNCE_COOLDOWN` to tune the compatibility delay.

Note: `Stop` means that the main agent stopped the current turn; it is not a whole-session exit event.

If you only want one notification after the whole Codex session exits, do not use `Stop`. Use the built-in wrapper:

```bash
python -m vibe_notification --wrap-codex
```

You can pass normal Codex arguments through unchanged:

```bash
python -m vibe_notification --wrap-codex -- --help
python -m vibe_notification --wrap-codex -- -C /path/to/project
```

If you want this as your everyday entrypoint, add a shell alias such as:

```bash
alias codexn='python3 -m vibe_notification --wrap-codex --'
```

Then launch `codexn`; VibeNotification will fire only once, after the Codex process actually exits.

To inspect your local integration and spot config/semantic mismatches quickly:

```bash
python -m vibe_notification --doctor
```

Typical placement in `config.toml`:

```toml
model_provider = "xxx"
model = "gpt-5.1-codex-max"
model_reasoning_effort = "medium"
disable_response_storage = true

[[hooks.Stop]]

[[hooks.Stop.hooks]]
type = "command"
command = "python3 -m vibe_notification"
timeout = 30

[model_providers.xxx]
name = "xxx"
base_url = "https://xxx/v1"
wire_api = "responses"
requires_openai_auth = true

[tui]
notifications = true
```

## Configuration Recipes

### Visual only (no sound)

- Codex `~/.codex/config.toml`:

```toml
command = "python3 -m vibe_notification --sound 0"
```

- Claude Code `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python -m vibe_notification --sound 0"
          }
        ]
      }
    ]
  }
}
```

- Quick test:

```bash
python -m vibe_notification --sound 0 --test
```

### Sound only (no system toast)

- Codex:

```toml
command = "python3 -m vibe_notification --notification 0"
```

- Claude Code:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python -m vibe_notification --notification 0"
          }
        ]
      }
    ]
  }
}
```

- Quick test:

```bash
python -m vibe_notification --notification 0 --test
```

### Temporary toggles (environment variables)

In a hook command, `env NAME=value command` sets an environment variable only for the command that follows it. For example:

```toml
command = "env VIBE_NOTIFICATION_SENDER_MODE=off python3 -m vibe_notification"
```

This does not permanently modify your shell or system environment. You can place multiple `NAME=value` assignments after `env`; the final arguments are the Python command to execute.

Common environment variables:

| Variable | Accepted values | Effect | Important notes |
|----------|-----------------|--------|-----------------|
| `VIBE_NOTIFICATION_SOUND` | `0` | Temporarily disable sound | Only `0` is recognized here; use CLI `--sound 1` to force sound on |
| `VIBE_NOTIFICATION_NOTIFY` | `0` | Temporarily disable system toasts | Does not disable sound; use CLI `--notification 1` to force toasts on |
| `VIBE_NOTIFICATION_SOUND_VOLUME` | `0.0`–`1.0` | Override sound volume | Values are clamped to the range; the config default is `0.1` |
| `VIBE_NOTIFICATION_SOUND_TYPE` | e.g. `Glass`, `Ping`, `Pop`, `Tink`, `Basso` | Override the alert sound | Available sounds depend on the operating system |
| `VIBE_NOTIFICATION_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | Override log level | `DEBUG` records more detail and can include raw Codex payloads |
| `VIBE_NOTIFICATION_LANGUAGE` | `zh`, `en` | Override UI language | Invalid values are ignored |
| `VIBE_NOTIFICATION_SENDER_MODE` | `auto`, `off`, `force` | Control macOS sender binding | Changes notification attribution, not whether a toast is sent |
| `VIBE_NOTIFICATION_SENDER_BUNDLE_ID` | a macOS Bundle ID | Select a sender explicitly | Advanced; only effective when sender mode is not `off` |
| `VIBE_ALLOW_LEGACY_CODEX_NOTIFY` | `1`, `true`, `yes`, `on` | Enable legacy Codex `notify` compatibility | Off by default; can misclassify an intermediate turn, so it is not recommended |
| `VIBE_DEBOUNCE_COOLDOWN` | a non-negative integer in seconds | Set the legacy `notify` quiet period | Relevant only when the previous option is enabled; defaults to `10` seconds |

For sound, toast, and log-level settings, precedence is: **CLI option > environment variable > `config.json` > built-in default**. Volume, sound type, language, and sender mode have no CLI equivalent, so their precedence is: **environment variable > `config.json` > built-in default**.

#### macOS sender modes

- `off`: Do not pass a host application Bundle ID to `terminal-notifier`. The notification is still sent and is normally attributed to `terminal-notifier`. This is recommended for Codex, Claude Code, and terminal hooks because it avoids inheriting VS Code or Terminal notification policies.
- `auto`: Detect the context. Normal GUI-hosted runs try to bind the detected host application, while Claude Code hooks and terminal-hosted runs automatically behave like `off`.
- `force`: Try to detect and bind the host application even from a terminal context. Use this only when you specifically want notifications attributed to VS Code, Terminal, or another host app.

`VIBE_NOTIFICATION_SENDER_MODE=off` is not the same as `VIBE_NOTIFICATION_NOTIFY=0`: the former disables sender binding only; the latter disables system toasts.

Codex examples (replace `command` under `[[hooks.Stop.hooks]]` above):

```toml
# Temporarily mute sound
command = "env VIBE_NOTIFICATION_SOUND=0 python3 -m vibe_notification"

# Disable all notifications (for debugging)
command = "env VIBE_NOTIFICATION_NOTIFY=0 VIBE_NOTIFICATION_SOUND=0 python3 -m vibe_notification"

# Enable debug logging
command = "env VIBE_NOTIFICATION_LOG_LEVEL=DEBUG python3 -m vibe_notification"
```

Claude Code example:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "env VIBE_NOTIFICATION_SOUND=0 VIBE_NOTIFICATION_SENDER_MODE=off python -m vibe_notification"
          }
        ]
      }
    ]
  }
}
```

CLI tests:

```bash
VIBE_NOTIFICATION_SOUND=0 python -m vibe_notification --test
VIBE_NOTIFICATION_SOUND=0 VIBE_NOTIFICATION_NOTIFY=0 python -m vibe_notification --test
VIBE_NOTIFICATION_LOG_LEVEL=DEBUG python -m vibe_notification --test
VIBE_NOTIFICATION_SENDER_MODE=off python -m vibe_notification --test
```

### Sound type

Available macOS sound types: `Glass` (default), `Ping`, `Pop`, `Tink`, `Basso`.

```toml
command = "env VIBE_NOTIFICATION_SOUND_TYPE=Ping python3 -m vibe_notification"
# Low tone
command = "env VIBE_NOTIFICATION_SOUND_TYPE=Basso python3 -m vibe_notification"
```

Claude Code:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "env VIBE_NOTIFICATION_SOUND_TYPE=Pop python -m vibe_notification"
          }
        ]
      }
    ]
  }
}
```

Test different sounds:

```bash
VIBE_NOTIFICATION_SOUND_TYPE=Tink python -m vibe_notification --test
VIBE_NOTIFICATION_SOUND_TYPE=Ping python -m vibe_notification --test
```

### Volume control

Volume range is `0.0–1.0`.

```toml
command = "env VIBE_NOTIFICATION_SOUND_VOLUME=0.2 python3 -m vibe_notification"
command = "env VIBE_NOTIFICATION_SOUND_VOLUME=0.5 python3 -m vibe_notification"
command = "env VIBE_NOTIFICATION_SOUND_VOLUME=0 python3 -m vibe_notification" # mute
```

Claude Code:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "env VIBE_NOTIFICATION_SOUND_VOLUME=0.3 python -m vibe_notification"
          }
        ]
      }
    ]
  }
}
```

Quick test:

```bash
VIBE_NOTIFICATION_SOUND_VOLUME=0.1 python -m vibe_notification --test
VIBE_NOTIFICATION_SOUND_VOLUME=0.8 python -m vibe_notification --test
```

### Notification timeout (current platform limitation)

Edit `~/.config/vibe-notification/config.json`:

```json
{
  "enable_sound": true,
  "enable_notification": true,
  "notification_timeout": 10000,
  "sound_type": "Glass",
  "sound_volume": 0.1,
  "log_level": "INFO"
}
```

`notification_timeout` is currently a reserved configuration field. The platform adapters do not yet pass it to the macOS, Linux, or Windows notification backends, so the value cannot guarantee dismissal after an exact number of milliseconds. Actual display duration is primarily controlled by operating-system notification style, notification-center settings, and focus mode. Keep the default `10000` for now, and do not rely on this field for timing-critical alerts.

Or use the interactive config:

```bash
python -m vibe_notification --config
```

### Prebuilt combos

Focus mode (low volume + gentle tone, with toast retained):

```toml
command = "env VIBE_NOTIFICATION_SOUND_VOLUME=0.1 VIBE_NOTIFICATION_SOUND_TYPE=Basso python3 -m vibe_notification"
```

Meeting mode (sound only, louder, specific tone):

```toml
command = "env VIBE_NOTIFICATION_NOTIFY=0 VIBE_NOTIFICATION_SOUND_VOLUME=0.7 VIBE_NOTIFICATION_SOUND_TYPE=Ping python3 -m vibe_notification"
```

Debug mode (keep current sound/toast toggles + debug logs):

```toml
command = "env VIBE_NOTIFICATION_LOG_LEVEL=DEBUG python3 -m vibe_notification"
```

## CLI Reference

### Command-line options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `event_json` | positional | - | Optional Codex event JSON string |
| `--test` | flag | - | Send a test notification |
| `--config` | flag | - | Interactive configuration |
| `--sound {0,1}` | choice | config value | Enable/disable sound (0=off, 1=on) |
| `--notification {0,1}` | choice | config value | Enable/disable system notification (0=off, 1=on) |
| `--log-level {DEBUG,INFO,WARNING,ERROR}` | choice | config value | Set log level |
| `--doctor` | flag | - | Check local Claude Code, Codex, VibeNotification, and notification-backend integration |
| `--wrap-codex` | flag | - | Launch Codex and notify once when its process exits; put Codex arguments after `--` |
| `--version` | flag | - | Show version |

### Config file

Location: `~/.config/vibe-notification/config.json`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enable_sound` | bool | `true` | Enable sound |
| `enable_notification` | bool | `true` | Enable system notification |
| `notification_timeout` | int | `10000` | Reserved; not currently applied by platform adapters |
| `sound_type` | string | `"Glass"` | Sound type |
| `sound_volume` | float | `0.1` | Sound volume |
| `log_level` | string | `"INFO"` | Log level |
| `detect_conversation_end` | bool | `true` | Detect end of conversation |
| `language` | string | `"zh"` | UI language: `zh` or `en` |
| `macos_sender_mode` | string | `"auto"` | Sender mode for macOS: `auto`, `off`, or `force` |

Additional notes:

- `"default"` in older `config.example.json` files and existing configs remains supported for compatibility.
- Keep `detect_conversation_end` set to `true`. When disabled, ordinary non-terminal events may follow legacy notification behavior, although explicitly suppressed safety events remain silent.
- `notification_timeout` is not currently applied by platform notification adapters; see “Notification timeout (current platform limitation)” above.

### Environment variables

| Env | Description | Example |
|-----|-------------|---------|
| `VIBE_NOTIFICATION_SOUND` | Override sound setting | `VIBE_NOTIFICATION_SOUND=0` |
| `VIBE_NOTIFICATION_NOTIFY` | Override notification setting | `VIBE_NOTIFICATION_NOTIFY=0` |
| `VIBE_NOTIFICATION_LOG_LEVEL` | Override log level | `VIBE_NOTIFICATION_LOG_LEVEL=DEBUG` |
| `VIBE_NOTIFICATION_SENDER_MODE` | Override macOS sender binding mode | `VIBE_NOTIFICATION_SENDER_MODE=off` |
| `VIBE_NOTIFICATION_SOUND_VOLUME` | Override and clamp volume to `0.0`–`1.0` | `VIBE_NOTIFICATION_SOUND_VOLUME=0.3` |
| `VIBE_NOTIFICATION_SOUND_TYPE` | Override the system alert sound | `VIBE_NOTIFICATION_SOUND_TYPE=Glass` |
| `VIBE_NOTIFICATION_LANGUAGE` | Override UI language | `VIBE_NOTIFICATION_LANGUAGE=en` |
| `VIBE_NOTIFICATION_SENDER_BUNDLE_ID` | Set the macOS sender Bundle ID | `VIBE_NOTIFICATION_SENDER_BUNDLE_ID=com.apple.Terminal` |
| `VIBE_ALLOW_LEGACY_CODEX_NOTIFY` | Explicitly enable unreliable legacy Codex notify debounce | `VIBE_ALLOW_LEGACY_CODEX_NOTIFY=1` |
| `VIBE_DEBOUNCE_COOLDOWN` | Legacy Codex notify quiet period in seconds | `VIBE_DEBOUNCE_COOLDOWN=30` |

### Typical commands

```bash
# Test (toast + sound)
python -m vibe_notification --test

# Toast only
python -m vibe_notification --sound 0 --test

# Sound only
python -m vibe_notification --notification 0 --test

# Debug logs
python -m vibe_notification --log-level DEBUG --test
```

### Integration checks

Check whether Codex and Claude Code use the recommended `Stop` hook, and inspect sound, toast, and macOS backend status:

```bash
python -m vibe_notification --doctor
```

Test whether the current settings can produce a toast and sound:

```bash
python -m vibe_notification --test
```

Legacy Codex `agent-turn-complete` JSON is only for compatibility when hooks are unavailable and is suppressed by default. Do not treat manually passing this JSON as the recommended Codex configuration or normal test path.

## Publishing to PyPI

1. Bump the version in `pyproject.toml` (single source of truth).
2. Install tooling: `python -m pip install --upgrade build twine`.
3. Build: `python -m build` (creates `.tar.gz` and `.whl` under `dist/`).
4. Validate: `python -m twine check dist/*`.
5. Upload: `TWINE_USERNAME=__token__ TWINE_PASSWORD=<pypi-token> python -m twine upload dist/*` (use `--repository testpypi` to dry run).
6. Install + verify: `pip install -U vibe-notification` then `python -m vibe_notification --test`.
