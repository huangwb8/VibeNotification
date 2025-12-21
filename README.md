# VibeNotification

让 Claude Code 或 Codex 的单轮对话结束时自动弹出系统通知并播放提示音的轻量工具。

## 安装

- 稳定版（PyPI）：`pip install vibe-notification`
- 开发版：`pip install -e .`
- 准备虚拟环境（可选）：`python -m venv venv && source venv/bin/activate`
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

> 适用于需要视觉提醒但保持环境安静的场合

**Codex 配置：**

```toml
# 在 ~/.codex/config.toml 中设置
notify = ["python3", "-m", "vibe_notification", "--sound", "0"]
```

**Claude Code 配置：**

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

**测试命令：**

```bash
# 验证只弹窗不响铃效果
python -m vibe_notification --sound 0 --test
```

#### 只响铃不弹窗

> 适用于需要听觉提醒但不希望被打断工作流的场景

**Codex 配置：**

```toml
# 在 ~/.codex/config.toml 中设置
notify = ["python3", "-m", "vibe_notification", "--notification", "0"]
```

**Claude Code 配置：**

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

**测试命令：**

```bash
# 验证只响铃不弹窗效果
python -m vibe_notification --notification 0 --test
```

#### 临时控制

> 无需修改配置文件，通过环境变量灵活控制通知行为

**环境变量说明：**

- `VIBE_NOTIFICATION_SOUND=0` - 临时禁用声音通知
- `VIBE_NOTIFICATION_NOTIFY=0` - 临时禁用系统通知
- `VIBE_NOTIFICATION_LOG_LEVEL=DEBUG` - 临时设置调试日志级别

**Codex 配置：**

```toml
# 在 ~/.codex/config.toml 中设置临时禁用声音
notify = ["env", "VIBE_NOTIFICATION_SOUND=0", "python3", "-m", "vibe_notification"]

# 完全禁用通知（调试用）
notify = ["env", "VIBE_NOTIFICATION_NOTIFY=0", "VIBE_NOTIFICATION_SOUND=0", "python3", "-m", "vibe_notification"]

# 启用调试日志
notify = ["env", "VIBE_NOTIFICATION_LOG_LEVEL=DEBUG", "python3", "-m", "vibe_notification"]
```

**Claude Code 配置：**

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

**测试命令：**

```bash
# 临时禁用声音通知
VIBE_NOTIFICATION_SOUND=0 python -m vibe_notification --test

# 临时禁用所有通知
VIBE_NOTIFICATION_SOUND=0 VIBE_NOTIFICATION_NOTIFY=0 python -m vibe_notification --test

# 临时启用调试日志
VIBE_NOTIFICATION_LOG_LEVEL=DEBUG python -m vibe_notification --test
```

#### 声音类型自定义

> 支持多种系统内置声音，可根据个人偏好选择

**可用声音类型：**

- `Glass` - 玻璃音效（默认）
- `Ping` - 清脆提示音
- `Pop` - 气泡音效
- `Tink` - 叮当声
- `Basso` - 低音提示

**Codex 配置：**

```toml
# 在 ~/.codex/config.toml 中设置不同声音类型
notify = ["env", "VIBE_NOTIFICATION_SOUND_TYPE=Ping", "python3", "-m", "vibe_notification"]

# 使用低音提示音
notify = ["env", "VIBE_NOTIFICATION_SOUND_TYPE=Basso", "python3", "-m", "vibe_notification"]
```

**Claude Code 配置：**

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

**测试命令：**

```bash
# 测试不同声音类型
VIBE_NOTIFICATION_SOUND_TYPE=Tink python -m vibe_notification --test
VIBE_NOTIFICATION_SOUND_TYPE=Ping python -m vibe_notification --test
```

#### 音量控制

> 精确控制提示音音量，适合不同环境需求

**Codex 配置：**

```toml
# 设置音量为 20% (0.0-1.0)
notify = ["env", "VIBE_NOTIFICATION_SOUND_VOLUME=0.2", "python3", "-m", "vibe_notification"]

# 设置音量为 50%
notify = ["env", "VIBE_NOTIFICATION_SOUND_VOLUME=0.5", "python3", "-m", "vibe_notification"]

# 静音模式（音量设为 0）
notify = ["env", "VIBE_NOTIFICATION_SOUND_VOLUME=0", "python3", "-m", "vibe_notification"]
```

**Claude Code 配置：**

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

**测试命令：**

```bash
# 测试不同音量
VIBE_NOTIFICATION_SOUND_VOLUME=0.1 python -m vibe_notification --test
VIBE_NOTIFICATION_SOUND_VOLUME=0.8 python -m vibe_notification --test
```

#### 通知持续时间控制

> 在配置文件中设置通知显示时间

**配置文件修改：**

```bash
# 编辑配置文件
~/.config/vibe-notification/config.json
```

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

**超时时间说明：**

- `5000` - 5秒自动消失
- `10000` - 10秒自动消失（默认）
- `30000` - 30秒自动消失
- `0` - 不会自动消失（需要手动关闭）

**交互式配置：**

```bash
# 通过交互式配置界面设置
python -m vibe_notification --config
```

#### 高级组合配置

> 组合多个环境变量实现个性化通知

**工作专注模式：**

```bash
# 低音量 + 只弹窗 + 短时间显示
notify = ["env", "VIBE_NOTIFICATION_SOUND_VOLUME=0.1", "VIBE_NOTIFICATION_SOUND_TYPE=Basso", "python3", "-m", "vibe_notification"]
```

**会议模式：**

```bash
# 只响铃 + 高音量 + 特定声音
notify = ["env", "VIBE_NOTIFICATION_NOTIFY=0", "VIBE_NOTIFICATION_SOUND_VOLUME=0.7", "VIBE_NOTIFICATION_SOUND_TYPE=Ping", "python3", "-m", "vibe_notification"]
```

**调试模式：**

```bash
# 启用所有通知 + 调试日志 + 长时间显示
notify = ["env", "VIBE_NOTIFICATION_LOG_LEVEL=DEBUG", "python3", "-m", "vibe_notification"]
```

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

## 发布到 PyPI

1. 更新版本号：同时修改 `pyproject.toml` 的 `version` 与 `vibe_notification/__init__.py` 的 `__version__`。
2. 安装发布工具：`python -m pip install --upgrade build twine`。
3. 构建发布物：`python -m build`（生成 `dist/` 下的 `.tar.gz` 与 `.whl`）。
4. 校验包体：`python -m twine check dist/*`。
5. 上传 PyPI：`TWINE_USERNAME=__token__ TWINE_PASSWORD=<pypi-token> python -m twine upload dist/*`；若先验证，可替换为 `--repository testpypi`。
6. 安装验证：`pip install -U vibe-notification` 并运行 `python -m vibe_notification --test`。
