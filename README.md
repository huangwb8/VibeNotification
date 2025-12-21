# VibeNotification

让 Claude Code 或 Codex 的单轮对话结束时自动弹出系统通知并播放提示音的轻量工具。

## 安装

- 准备虚拟环境（可选）：`python -m venv venv && source venv/bin/activate`
- 开发模式安装：`pip install -e .`
- 验证环境：`python -m vibe_notification --test`（会弹窗并响铃，如果已启用）
- 交互式配置：`python -m vibe_notification --config`
  - 默认配置文件：`~/.config/vibe-notification/config.json`
  - 确保“声音通知”和“系统通知”均为启用状态

## 快速开始

### Claude Code

> 配置 ~/.claude/settings.json
> - **Stop 钩子**：每当 Claude 完成一次回复时触发
> - **SessionEnd 钩子**：当 Claude Code 会话结束时触发
> - **SubagentStop 钩子**：当子代理（Task 工具）完成时触发

Claude Code 提供了多种钩子事件，您可以根据需要选择：

#### AI回复完成时通知

> 希望 Claude 每次完成回复后立即收到通知，方便及时查看结果。这是最好的特性！

- **编辑配置文件**：
```bash
# 配置文件路径
~/.claude/settings.json
```

- **添加 Stop 钩子**：
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

- 设置在settings.json里的具体位置

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

#### 会话结束时通知

> 仅在退出 Claude Code 时收到通知。个人感觉并不实用。

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

#### 同时使用多个钩子

> 既想知道每次回复完成，也想知道会话结束。

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

### Codex

> 如果希望在 Codex CLI里回复结束自动通知，可在 Codex `~/.codex/config.toml` 里配置 `notify`，让 Codex 在每次 `agent-turn-complete` 时调用 VibeNotification。  

#### 每次回复完成时通知（推荐）✨

- 打开 `~/.codex/config.toml`，添加：

```toml
# Codex 通知钩子：将事件 JSON 传给 VibeNotification
notify = ["python3", "-m", "vibe_notification"] 
```

- 相关配置在config.toml文件的位置如下：

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

### 其它配置

#### 只弹窗不响铃

`notify = ["python3","-m","vibe_notification","--sound","0"]`

#### 只响铃不弹窗

`notify = ["python3","-m","vibe_notification","--notification","0"]`

#### 临时控制

在命令前增加环境变量，例如 `notify = ["env","VIBE_NOTIFICATION_SOUND=0","python3","-m","vibe_notification"]`

## 进阶使用

### 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `event_json` | 位置参数 | - | Codex 事件 JSON 字符串（可选） |
| `--test` | 标志 | - | 测试模式，发送测试通知 |
| `--config` | 标志 | - | 交互式配置模式 |
| `--sound {0,1}` | 选项 | 配置文件值 | 启用/禁用声音通知 (0=禁用, 1=启用) |
| `--notification {0,1}` | 选项 | 配置文件值 | 启用/禁用系统通知 (0=禁用, 1=启用) |
| `--log-level {DEBUG,INFO,WARNING,ERROR}` | 选项 | 配置文件值 | 设置日志级别 |
| `--version` | 标志 | - | 显示版本信息 |

### 配置文件参数

配置文件位置：`~/.config/vibe-notification/config.json`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enable_sound` | 布尔 | `true` | 是否启用声音通知 |
| `enable_notification` | 布尔 | `true` | 是否启用系统通知 |
| `notification_timeout` | 整数 | `10000` | 通知显示时间（毫秒） |
| `sound_type` | 字符串 | `"default"` | 声音类型 |
| `log_level` | 字符串 | `"INFO"` | 日志级别 |
| `detect_conversation_end` | 布尔 | `true` | 是否检测会话结束 |

### 环境变量参数

| 环境变量 | 说明 | 示例 |
|----------|------|------|
| `VIBE_NOTIFICATION_SOUND` | 覆盖声音通知设置 | `VIBE_NOTIFICATION_SOUND=0` |
| `VIBE_NOTIFICATION_NOTIFY` | 覆盖系统通知设置 | `VIBE_NOTIFICATION_NOTIFY=0` |
| `VIBE_NOTIFICATION_LOG_LEVEL` | 覆盖日志级别设置 | `VIBE_NOTIFICATION_LOG_LEVEL=DEBUG` |

### 基础用法

```bash
# 测试通知（弹窗+声音）
python -m vibe_notification --test

# 只弹窗不响铃
python -m vibe_notification --sound 0 --test

# 只响铃不弹窗
python -m vibe_notification --notification 0 --test

# 设置日志级别为 DEBUG
python -m vibe_notification --log-level DEBUG --test
```

### Claude Code 钩子使用

```bash
# 作为 Stop 钩子使用（每次回复完成时）
echo '{"toolName": "Bash"}' | python -m vibe_notification

# 临时关闭声音通知
VIBE_NOTIFICATION_SOUND=0 echo '{"toolName": "Task"}' | python -m vibe_notification

# 临时关闭所有通知
VIBE_NOTIFICATION_NOTIFY=0 python -m vibe_notification
```

### Codex 钩子使用

```bash
# 直接传递 JSON 事件
python -m vibe_notification '{"type":"agent-turn-complete","agent":"codex","message":"工具 Bash 完成"}'

# 组合参数使用
python -m vibe_notification '{"type":"agent-turn-complete","agent":"codex"}' --notification 1 --sound 0

# 环境变量控制
VIBE_NOTIFICATION_SOUND=1 VIBE_NOTIFICATION_NOTIFY=1 python -m vibe_notification '{"type":"agent-turn-complete"}'
```

### 配置管理

```bash
# 交互式配置
python -m vibe_notification --config

# 查看版本
python -m vibe_notification --version

# 查看帮助
python -m vibe_notification --help
```

### 高级组合用法

```bash
# Claude Code 中临时启用调试日志并关闭声音
python -m vibe_notification --log-level DEBUG --sound 0

# Codex 中强制启用系统通知（即使配置文件中关闭了）
python -m vibe_notification '{"type":"agent-turn-complete"}' --notification 1

# 环境变量和命令行参数组合（环境变量优先级更高）
VIBE_NOTIFICATION_SOUND=0 python -m vibe_notification --sound 1 --test
# 结果：声音仍然被禁用（环境变量覆盖命令行参数）
```