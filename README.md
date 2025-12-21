<div align="center">

# VibeNotification

[![PyPI](https://img.shields.io/pypi/v/vibe-notification.svg)](https://pypi.org/project/vibe-notification/)
[![Python](https://img.shields.io/pypi/pyversions/vibe-notification.svg)](https://pypi.org/project/vibe-notification/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)](#installation)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

English | [中文](README.zh.md)

<strong>Toast + chime when Claude Code or Codex finishes—plug in a hook and stop waiting on terminals.</strong>

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

- Hooks you can use: `Stop` (on every reply), `SessionEnd` (when the session ends), `SubagentStop` (Task tool completes)
- Edit `~/.claude/settings.json` and add a Stop hook:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python -m vibe_notification"
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
            "command": "python -m vibe_notification",
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

- Session end only:

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python -m vibe_notification"
          }
        ]
      }
    ]
  }
}
```

- Combine multiple hooks (Stop + SessionEnd):

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python -m vibe_notification"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python -m vibe_notification"
          }
        ]
      }
    ]
  }
}
```

### Codex CLI

Add a notifier command to `~/.codex/config.toml` so Codex triggers VibeNotification on every `agent-turn-complete`:

```toml
notify = ["python3", "-m", "vibe_notification"]
```

Typical placement in `config.toml`:

```toml
model_provider = "xxx"
model = "gpt-5.1-codex-max"
model_reasoning_effort = "medium"
disable_response_storage = true
notify = ["python3", "-m", "vibe_notification"]

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
notify = ["python3", "-m", "vibe_notification", "--sound", "0"]
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
notify = ["python3", "-m", "vibe_notification", "--notification", "0"]
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

- `VIBE_NOTIFICATION_SOUND=0` — mute sound
- `VIBE_NOTIFICATION_NOTIFY=0` — disable system notification
- `VIBE_NOTIFICATION_LOG_LEVEL=DEBUG` — enable debug logging

Codex examples:

```toml
# Temporarily mute sound
notify = ["env", "VIBE_NOTIFICATION_SOUND=0", "python3", "-m", "vibe_notification"]

# Disable all notifications (for debugging)
notify = ["env", "VIBE_NOTIFICATION_NOTIFY=0", "VIBE_NOTIFICATION_SOUND=0", "python3", "-m", "vibe_notification"]

# Enable debug logging
notify = ["env", "VIBE_NOTIFICATION_LOG_LEVEL=DEBUG", "python3", "-m", "vibe_notification"]
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
            "command": "env VIBE_NOTIFICATION_SOUND=0 python -m vibe_notification"
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
```

### Sound type

Available macOS sound types: `Glass` (default), `Ping`, `Pop`, `Tink`, `Basso`.

```toml
notify = ["env", "VIBE_NOTIFICATION_SOUND_TYPE=Ping", "python3", "-m", "vibe_notification"]
# Low tone
notify = ["env", "VIBE_NOTIFICATION_SOUND_TYPE=Basso", "python3", "-m", "vibe_notification"]
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
notify = ["env", "VIBE_NOTIFICATION_SOUND_VOLUME=0.2", "python3", "-m", "vibe_notification"]
notify = ["env", "VIBE_NOTIFICATION_SOUND_VOLUME=0.5", "python3", "-m", "vibe_notification"]
notify = ["env", "VIBE_NOTIFICATION_SOUND_VOLUME=0", "python3", "-m", "vibe_notification"] # mute
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

### Notification timeout

Edit `~/.config/vibe-notification/config.json`:

```json
{
  "enable_sound": true,
  "enable_notification": true,
  "notification_timeout": 5000,
  "sound_type": "Glass",
  "sound_volume": 0.1,
  "log_level": "INFO"
}
```

- `5000` = 5s auto-dismiss
- `10000` = 10s (default)
- `30000` = 30s
- `0` = sticky, manual close

Or use the interactive config:

```bash
python -m vibe_notification --config
```

### Prebuilt combos

Focus mode (low volume + toast only + short display):

```toml
notify = ["env", "VIBE_NOTIFICATION_SOUND_VOLUME=0.1", "VIBE_NOTIFICATION_SOUND_TYPE=Basso", "python3", "-m", "vibe_notification"]
```

Meeting mode (sound only, louder, specific tone):

```toml
notify = ["env", "VIBE_NOTIFICATION_NOTIFY=0", "VIBE_NOTIFICATION_SOUND_VOLUME=0.7", "VIBE_NOTIFICATION_SOUND_TYPE=Ping", "python3", "-m", "vibe_notification"]
```

Debug mode (all on + debug logs):

```toml
notify = ["env", "VIBE_NOTIFICATION_LOG_LEVEL=DEBUG", "python3", "-m", "vibe_notification"]
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
| `--version` | flag | - | Show version |

### Config file

Location: `~/.config/vibe-notification/config.json`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enable_sound` | bool | `true` | Enable sound |
| `enable_notification` | bool | `true` | Enable system notification |
| `notification_timeout` | int | `10000` | Duration in ms |
| `sound_type` | string | `"default"` | Sound type |
| `log_level` | string | `"INFO"` | Log level |
| `detect_conversation_end` | bool | `true` | Detect end of conversation |

### Environment variables

| Env | Description | Example |
|-----|-------------|---------|
| `VIBE_NOTIFICATION_SOUND` | Override sound setting | `VIBE_NOTIFICATION_SOUND=0` |
| `VIBE_NOTIFICATION_NOTIFY` | Override notification setting | `VIBE_NOTIFICATION_NOTIFY=0` |
| `VIBE_NOTIFICATION_LOG_LEVEL` | Override log level | `VIBE_NOTIFICATION_LOG_LEVEL=DEBUG` |

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

### Hook usage examples

Claude Code:

```bash
echo '{"toolName": "Bash"}' | python -m vibe_notification
VIBE_NOTIFICATION_SOUND=0 echo '{"toolName": "Task"}' | python -m vibe_notification
VIBE_NOTIFICATION_NOTIFY=0 python -m vibe_notification
```

Codex:

```bash
python -m vibe_notification '{"type":"agent-turn-complete","agent":"codex","message":"tool Bash done"}'
python -m vibe_notification '{"type":"agent-turn-complete","agent":"codex"}' --notification 1 --sound 0
VIBE_NOTIFICATION_SOUND=1 VIBE_NOTIFICATION_NOTIFY=1 python -m vibe_notification '{"type":"agent-turn-complete"}'
```

## Publishing to PyPI

1. Bump the version in `pyproject.toml` (single source of truth).
2. Install tooling: `python -m pip install --upgrade build twine`.
3. Build: `python -m build` (creates `.tar.gz` and `.whl` under `dist/`).
4. Validate: `python -m twine check dist/*`.
5. Upload: `TWINE_USERNAME=__token__ TWINE_PASSWORD=<pypi-token> python -m twine upload dist/*` (use `--repository testpypi` to dry run).
6. Install + verify: `pip install -U vibe-notification` then `python -m vibe_notification --test`.
