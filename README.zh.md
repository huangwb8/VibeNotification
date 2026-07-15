<div align="center">

# VibeNotification

[![PyPI](https://img.shields.io/pypi/v/vibe-notification.svg)](https://pypi.org/project/vibe-notification/)
[![Python](https://img.shields.io/pypi/pyversions/vibe-notification.svg)](https://pypi.org/project/vibe-notification/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)](#%E5%AE%89%E8%A3%85)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[English](README.md) | 中文

<strong>在 Claude Code 或 Codex 回复结束时自动弹窗+提示音的轻量工具，让你不用守着终端等结果。</strong>

[博客教程：AI应用系列 一个简单的 Vibe coding 的通知系统](https://blognas.hwb0307.com/ai/6659)

</div>

![image-20251221214216954](https://chevereto.hwb0307.com/images/2025/12/21/image-20251221214216954.png)

## 安装

- 稳定版（PyPI）：`pip install vibe-notification`
- 开发版：`pip install -e .`
- 可选虚拟环境：`python -m venv venv && source venv/bin/activate`
- 验证：`python -m vibe_notification --test`（如已启用会弹窗+响铃）
- 交互式配置：`python -m vibe_notification --config`
  - 默认配置文件：`~/.config/vibe-notification/config.json`
  - 请确保声音通知和系统通知均为开启状态

## 快速开始

### Claude Code

- 推荐钩子：`Stop`（每次主回复完成）。
- 如果你要的是“某个回复结束就通知”，直接用 `Stop`，这也是默认且唯一推荐的钩子。
- 不建议把通知命令挂到 `SessionEnd` 或 `SubagentStop`：VibeNotification 默认会忽略它们，避免会话退出、子代理完成或工具链事件造成重复提示。
- 在 macOS 下，VibeNotification 现在会在 Claude Code hook 场景和终端宿主 CLI 场景默认关闭 `sender` 绑定，以提高横幅弹窗稳定性；如需强制沿用宿主 App 图标/归属，可设置 `VIBE_NOTIFICATION_SENDER_MODE=force`。
- 如果通知只进入通知中心，请到 `系统设置 > 通知` 检查当前生效的应用（`sender=off` 时通常是 `terminal-notifier`，`auto/force` 时通常是 VS Code / Terminal 等宿主 App），确认“允许通知”已打开、样式为横幅/提醒，且没有被专注模式压制。
- 在 `~/.claude/settings.json` 添加 Stop 钩子：

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

- 示例完整配置片段：

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

推荐在 `~/.codex/config.toml` 中使用 `Stop` hook。它在主代理经过工具调用和多轮工作、停止本轮输出时触发；收到用户消息、子代理结束和整个 Session 退出都不会触发完成通知：

```toml
[[hooks.Stop]]

[[hooks.Stop.hooks]]
type = "command"
command = "python3 -m vibe_notification"
timeout = 30
```

不要同时配置上述 `Stop` hook 和旧版 `notify`，否则同一任务可能从两条事件通道进入。旧 `notify` 的 `agent-turn-complete` 负载不包含 `commentary` / `final_answer` 阶段，固定静默期无法可靠判断最终回复，因此 VibeNotification 默认静默跳过旧 `notify`。仅当旧版 Codex 无法使用 hooks 时，才可显式设置 `VIBE_ALLOW_LEGACY_CODEX_NOTIFY=1` 恢复 10 秒尾沿防抖兼容；该模式仍可能把长时间工具调用之间的过程 turn 误判为结束。`VIBE_DEBOUNCE_COOLDOWN` 可调整兼容静默秒数。

注意：`Stop` 是“本轮主代理停止输出”，不是整个 Codex 会话退出。

如果你只希望在整个 Codex 会话退出后再通知，不要使用 `Stop`，改用内置 wrapper：

```bash
python -m vibe_notification --wrap-codex
```

如果你平时会带参数启动 Codex，也可以原样透传：

```bash
python -m vibe_notification --wrap-codex -- --help
python -m vibe_notification --wrap-codex -- -C /path/to/project
```

想把它当成日常入口的话，可以在 shell 里加一个别名，例如：

```bash
alias codexn='python3 -m vibe_notification --wrap-codex --'
```

之后直接用 `codexn` 启动；这样只有当 Codex 进程真正退出时，VibeNotification 才会发送一次通知。

想快速检查本机接入状态，也可以运行：

```bash
python -m vibe_notification --doctor
```

典型配置位置：

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

## 配置示例

### 只弹窗不响铃

- Codex `~/.codex/config.toml`：

```toml
command = "python3 -m vibe_notification --sound 0"
```

- Claude Code `~/.claude/settings.json`：

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

- 测试：

```bash
python -m vibe_notification --sound 0 --test
```

### 只响铃不弹窗

- Codex：

```toml
command = "python3 -m vibe_notification --notification 0"
```

- Claude Code：

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

- 测试：

```bash
python -m vibe_notification --notification 0 --test
```

### 临时控制（环境变量）

在 hook 命令中，`env 变量=值 命令` 表示只为后面的命令临时设置环境变量。例如：

```toml
command = "env VIBE_NOTIFICATION_SENDER_MODE=off python3 -m vibe_notification"
```

这不会永久修改 shell 或系统环境。`env` 后面可以连续放置多个 `变量=值`，最后才是要执行的 Python 命令。

常用环境变量如下：

| 变量 | 可用值 | 作用 | 重要说明 |
|------|--------|------|----------|
| `VIBE_NOTIFICATION_SOUND` | `0` | 临时关闭声音 | 这里只识别 `0`；如需强制开启，使用 CLI `--sound 1` |
| `VIBE_NOTIFICATION_NOTIFY` | `0` | 临时关闭系统弹窗 | 不影响声音；如需强制开启，使用 CLI `--notification 1` |
| `VIBE_NOTIFICATION_SOUND_VOLUME` | `0.0`–`1.0` | 覆盖声音音量 | 超出范围会被截断到 `0.0` 或 `1.0`，默认配置为 `0.1` |
| `VIBE_NOTIFICATION_SOUND_TYPE` | 如 `Glass`、`Ping`、`Pop`、`Tink`、`Basso` | 覆盖提示音 | 具体可用声音受操作系统影响 |
| `VIBE_NOTIFICATION_LOG_LEVEL` | `DEBUG`、`INFO`、`WARNING`、`ERROR` | 覆盖日志级别 | `DEBUG` 会记录更详细信息，可能包含 Codex 原始 payload |
| `VIBE_NOTIFICATION_LANGUAGE` | `zh`、`en` | 覆盖界面语言 | 非法值会被忽略 |
| `VIBE_NOTIFICATION_SENDER_MODE` | `auto`、`off`、`force` | 控制 macOS 通知 sender 绑定 | 仅影响通知归属和展示稳定性，不会关闭弹窗 |
| `VIBE_NOTIFICATION_SENDER_BUNDLE_ID` | macOS Bundle ID | 指定 sender | 仅在 sender mode 不是 `off` 时生效，属于高级设置 |
| `VIBE_ALLOW_LEGACY_CODEX_NOTIFY` | `1`、`true`、`yes`、`on` | 启用旧 Codex `notify` 兼容 | 默认关闭；可能把过程 turn 误判为结束，不推荐日常使用 |
| `VIBE_DEBOUNCE_COOLDOWN` | 非负整数秒 | 设置旧 `notify` 静默期 | 仅在上一项已启用时有意义，默认 `10` 秒 |

对于声音、弹窗和日志级别，优先级为：**CLI 参数 > 环境变量 > `config.json` > 内置默认值**。音量、音色、语言和 sender mode 没有对应 CLI 参数，因此是：**环境变量 > `config.json` > 内置默认值**。

#### macOS sender mode 详解

- `off`：不向 `terminal-notifier` 传递宿主 App 的 Bundle ID。通知仍然会发送，通常归属于 `terminal-notifier`；推荐用于 Codex、Claude Code 和终端 hook，可避免继承 VS Code、Terminal 等宿主 App 的通知策略。
- `auto`：自动判断运行环境。普通图形应用场景会尝试绑定检测到的宿主 App；Claude Code hook 或终端宿主场景会自动按 `off` 处理。
- `force`：即使运行在终端宿主中也尝试检测并绑定宿主 App。只有确实希望通知显示为 VS Code、Terminal 等应用时才使用。

`VIBE_NOTIFICATION_SENDER_MODE=off` 与 `VIBE_NOTIFICATION_NOTIFY=0` 完全不同：前者只关闭 sender 绑定，后者才是关闭系统弹窗。

Codex 示例（替换上文 `[[hooks.Stop.hooks]]` 中的 `command`）：

```toml
# 静音
command = "env VIBE_NOTIFICATION_SOUND=0 python3 -m vibe_notification"

# 完全禁用通知
command = "env VIBE_NOTIFICATION_NOTIFY=0 VIBE_NOTIFICATION_SOUND=0 python3 -m vibe_notification"

# 调试日志
command = "env VIBE_NOTIFICATION_LOG_LEVEL=DEBUG python3 -m vibe_notification"
```

Claude Code 示例：

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

测试命令：

```bash
VIBE_NOTIFICATION_SOUND=0 python -m vibe_notification --test
VIBE_NOTIFICATION_SOUND=0 VIBE_NOTIFICATION_NOTIFY=0 python -m vibe_notification --test
VIBE_NOTIFICATION_LOG_LEVEL=DEBUG python -m vibe_notification --test
VIBE_NOTIFICATION_SENDER_MODE=off python -m vibe_notification --test
```

### 声音类型

可选（macOS 内置）：`Glass`（默认）、`Ping`、`Pop`、`Tink`、`Basso`。

```toml
command = "env VIBE_NOTIFICATION_SOUND_TYPE=Ping python3 -m vibe_notification"
# 低音
command = "env VIBE_NOTIFICATION_SOUND_TYPE=Basso python3 -m vibe_notification"
```

Claude Code：

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

声音测试：

```bash
VIBE_NOTIFICATION_SOUND_TYPE=Tink python -m vibe_notification --test
VIBE_NOTIFICATION_SOUND_TYPE=Ping python -m vibe_notification --test
```

### 音量控制

范围 `0.0–1.0`：

```toml
command = "env VIBE_NOTIFICATION_SOUND_VOLUME=0.2 python3 -m vibe_notification"
command = "env VIBE_NOTIFICATION_SOUND_VOLUME=0.5 python3 -m vibe_notification"
command = "env VIBE_NOTIFICATION_SOUND_VOLUME=0 python3 -m vibe_notification" # 静音
```

Claude Code：

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

快速测试：

```bash
VIBE_NOTIFICATION_SOUND_VOLUME=0.1 python -m vibe_notification --test
VIBE_NOTIFICATION_SOUND_VOLUME=0.8 python -m vibe_notification --test
```

### 通知时长（当前平台限制）

编辑 `~/.config/vibe-notification/config.json`：

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

`notification_timeout` 当前是保留配置字段，通知适配器尚未把它传递给 macOS、Linux 或 Windows 的系统通知后端，因此不能保证按这里的毫秒数关闭。实际展示时长主要由操作系统的通知样式、通知中心和专注模式设置决定。建议暂时保留默认值 `10000`；不要依赖该字段实现必须精确计时的提醒。

或使用交互式配置：

```bash
python -m vibe_notification --config
```

### 组合模式

专注模式（低音量 + 柔和音色，保留弹窗）：

```toml
command = "env VIBE_NOTIFICATION_SOUND_VOLUME=0.1 VIBE_NOTIFICATION_SOUND_TYPE=Basso python3 -m vibe_notification"
```

会议模式（只响铃 + 较高音量 + 特定音色）：

```toml
command = "env VIBE_NOTIFICATION_NOTIFY=0 VIBE_NOTIFICATION_SOUND_VOLUME=0.7 VIBE_NOTIFICATION_SOUND_TYPE=Ping python3 -m vibe_notification"
```

调试模式（保持当前声音/弹窗开关 + 调试日志）：

```toml
command = "env VIBE_NOTIFICATION_LOG_LEVEL=DEBUG python3 -m vibe_notification"
```

## CLI 参考

### 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `event_json` | 位置参数 | - | 可选的 Codex 事件 JSON |
| `--test` | 标志 | - | 发送测试通知 |
| `--config` | 标志 | - | 交互式配置 |
| `--sound {0,1}` | 选项 | 配置值 | 0 关闭/1 开启声音 |
| `--notification {0,1}` | 选项 | 配置值 | 0 关闭/1 开启弹窗 |
| `--log-level {DEBUG,INFO,WARNING,ERROR}` | 选项 | 配置值 | 设置日志级别 |
| `--doctor` | 标志 | - | 检查 Claude Code、Codex、本项目和通知后端的本地集成状态 |
| `--wrap-codex` | 标志 | - | 启动 Codex，并仅在 Codex 进程退出后提醒一次；Codex 参数放在 `--` 后 |
| `--version` | 标志 | - | 显示版本 |

### 配置文件

位置：`~/.config/vibe-notification/config.json`

| 键 | 类型 | 默认值 | 说明 |
|----|------|--------|------|
| `enable_sound` | 布尔 | `true` | 启用声音 |
| `enable_notification` | 布尔 | `true` | 启用系统通知 |
| `notification_timeout` | 整数 | `10000` | 保留字段；当前平台适配器尚未应用 |
| `sound_type` | 字符串 | `"Glass"` | 声音类型 |
| `sound_volume` | 浮点 | `0.1` | 音量大小 |
| `log_level` | 字符串 | `"INFO"` | 日志级别 |
| `detect_conversation_end` | 布尔 | `true` | 检测会话结束 |
| `language` | 字符串 | `"zh"` | 界面语言：`zh` 或 `en` |
| `macos_sender_mode` | 字符串 | `"auto"` | macOS sender 模式：`auto`、`off`、`force` |

补充说明：

- 旧版 `config.example.json` 或已有配置中的 `"default"` 音色仍受兼容支持。
- `detect_conversation_end` 建议保持 `true`。关闭后普通非结束事件可能按旧行为进入通知流程，但显式标记为必须忽略的安全事件仍不会通知。
- `notification_timeout` 当前尚未由平台通知适配器应用，详见上文“通知时长（当前平台限制）”。

### 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `VIBE_NOTIFICATION_SOUND` | 覆盖声音设置 | `VIBE_NOTIFICATION_SOUND=0` |
| `VIBE_NOTIFICATION_NOTIFY` | 覆盖弹窗设置 | `VIBE_NOTIFICATION_NOTIFY=0` |
| `VIBE_NOTIFICATION_LOG_LEVEL` | 覆盖日志级别 | `VIBE_NOTIFICATION_LOG_LEVEL=DEBUG` |
| `VIBE_NOTIFICATION_SENDER_MODE` | 覆盖 macOS sender 模式 | `VIBE_NOTIFICATION_SENDER_MODE=off` |
| `VIBE_NOTIFICATION_SOUND_VOLUME` | 覆盖音量并限制在 `0.0`–`1.0` | `VIBE_NOTIFICATION_SOUND_VOLUME=0.3` |
| `VIBE_NOTIFICATION_SOUND_TYPE` | 覆盖系统提示音 | `VIBE_NOTIFICATION_SOUND_TYPE=Glass` |
| `VIBE_NOTIFICATION_LANGUAGE` | 覆盖界面语言 | `VIBE_NOTIFICATION_LANGUAGE=zh` |
| `VIBE_NOTIFICATION_SENDER_BUNDLE_ID` | 指定 macOS sender Bundle ID | `VIBE_NOTIFICATION_SENDER_BUNDLE_ID=com.apple.Terminal` |
| `VIBE_ALLOW_LEGACY_CODEX_NOTIFY` | 显式启用不可靠的旧 Codex notify 防抖兼容 | `VIBE_ALLOW_LEGACY_CODEX_NOTIFY=1` |
| `VIBE_DEBOUNCE_COOLDOWN` | 旧 Codex notify 兼容静默期（秒） | `VIBE_DEBOUNCE_COOLDOWN=30` |

### 常用命令

```bash
# 测试（弹窗+声音）
python -m vibe_notification --test

# 仅弹窗
python -m vibe_notification --sound 0 --test

# 仅声音
python -m vibe_notification --notification 0 --test

# 调试日志
python -m vibe_notification --log-level DEBUG --test
```

### 集成检查

检查 Codex/Claude Code 是否使用了推荐的 `Stop` hook，并确认声音、弹窗和 macOS 后端状态：

```bash
python -m vibe_notification --doctor
```

单独验证当前设置是否能发出弹窗和声音：

```bash
python -m vibe_notification --test
```

旧 Codex `agent-turn-complete` JSON 仅用于无法使用 hooks 的兼容场景，默认会被静默跳过。不要把手工传入这类 JSON 当作推荐的 Codex 配置或常规测试方式。

## 发布到 PyPI

1. 更新版本号：仅修改 `pyproject.toml`（唯一来源）。
2. 安装工具：`python -m pip install --upgrade build twine`。
3. 构建：`python -m build`（生成 `dist/` 下 `.tar.gz` 与 `.whl`）。
4. 校验：`python -m twine check dist/*`。
5. 上传：`TWINE_USERNAME=__token__ TWINE_PASSWORD=<pypi-token> python -m twine upload dist/*`（先验证可用 `--repository testpypi`）。
6. 安装验证：`pip install -U vibe-notification` 后运行 `python -m vibe_notification --test`。
