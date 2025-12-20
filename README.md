# VibeNotification

让 Claude Code 或 Codex 的单轮对话结束时自动弹出系统通知并播放提示音的轻量工具。

## 安装与快速验证

- 准备虚拟环境（可选）：`python -m venv venv && source venv/bin/activate`
- 开发模式安装：`pip install -e .`
- 验证环境：`python -m vibe_notification --test`（会弹窗并响铃，如果已启用）

## 基础配置

- 交互式配置：`python -m vibe_notification --config`
  - 默认配置文件：`~/.config/vibe-notification/config.json`
  - 确保“声音通知”和“系统通知”均为启用状态
- 快速切换（可与其它参数组合）：`python -m vibe_notification --sound 1 --notification 1 --log-level INFO`
- 环境变量覆盖：`VIBE_NOTIFICATION_SOUND=0` 或 `VIBE_NOTIFICATION_NOTIFY=0` 可临时关闭

## 快速开始

### Claude Code

> 配置 ~/.claude/settings.json
> - **Stop 钩子**：每当 Claude 完成一次回复时触发
> - **SessionEnd 钩子**：当 Claude Code 会话结束时触发
> - **SubagentStop 钩子**：当子代理（Task 工具）完成时触发

Claude Code 提供了多种钩子事件，您可以根据需要选择：

#### 每次回复完成时通知（推荐）✨

**适用场景**：希望 Claude 每次完成回复后立即收到通知，方便及时查看结果。

1. **编辑配置文件**：
   ```bash
   # 配置文件路径
   ~/.claude/settings.json
   ```

2. **添加 Stop 钩子**：
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

#### 会话结束时通知

**适用场景**：仅在退出 Claude Code 时收到通知。

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

**适用场景**：既想知道每次回复完成，也想知道会话结束。

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

### 高级配置选项

**条件触发通知**（仅特定工具触发）：
```json
{
  "hooks": {
    "post-tool": [
      {
        "command": ["python", "-m", "vibe_notification"],
        "condition": {
          "toolName": ["Task", "Bash", "Edit"]
        }
      }
    ]
  }
}
```

**自定义通知参数**：
```json
{
  "hooks": {
    "post-tool": [
      ["python", "-m", "vibe_notification", "--sound", "1", "--notification", "1"]
    ]
  }
}
```

### Codex

> 如果希望在 Codex CLI里回复结束自动通知，可在 Codex `~/.codex/config.toml` 里配置 `notify`，让 Codex 在每次 `agent-turn-complete` 时调用 VibeNotification。  

#### 每次回复完成时通知（推荐）✨

- 打开 `~/.codex/config.toml`，添加（或合并）：

```toml
model_provider = "packycode"
model = "gpt-5.1-codex-max"
model_reasoning_effort = "medium"
disable_response_storage = true
notify = ["python3", "-m", "vibe_notification"] # Codex 通知钩子：将事件 JSON 传给 VibeNotification

[model_providers.packycode]
name = "packycode"
base_url = "https://codex-api.packycode.com/v1"
wire_api = "responses"
requires_openai_auth = true

[tui]
notifications = true
```

