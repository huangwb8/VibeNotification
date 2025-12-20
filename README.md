# VibeNotification

让 Claude Code 或 Codex 的单轮对话结束时自动弹出系统通知并播放提示音的轻量工具。

## 安装与快速验证
- 准备虚拟环境：`python -m venv venv && source venv/bin/activate`
- 开发模式安装：`pip install -e .`
- 验证环境：`python -m vibe_notification --test`（会弹窗并响铃，如果已启用）

## 基础配置
- 交互式配置：`python -m vibe_notification --config`
  - 默认配置文件：`~/.config/vibe-notification/config.json`
  - 确保“声音通知”和“系统通知”均为启用状态
- 快速切换（可与其它参数组合）：`python -m vibe_notification --sound 1 --notification 1 --log-level INFO`
- 环境变量覆盖：`VIBE_NOTIFICATION_SOUND=0` 或 `VIBE_NOTIFICATION_NOTIFY=0` 可临时关闭

## Claude Code 钩子：回复完成即通知

### 方法一：配置 ~/.claude/settings.json（推荐）

Claude Code 提供了多种钩子事件，您可以根据需要选择：

#### 选项 A：每次回复完成时通知（推荐）✨

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

#### 选项 B：会话结束时通知

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

#### 选项 C：同时使用多个钩子

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

#### 配置说明

- **Stop 钩子**：每当 Claude 完成一次回复时触发
- **SessionEnd 钩子**：当 Claude Code 会话结束时触发
- **SubagentStop 钩子**：当子代理（Task 工具）完成时触发
- 使用虚拟环境时需指定完整路径：`/path/to/venv/bin/python -m vibe_notification`

#### 验证配置

```bash
# 1. 检查配置文件格式
python -m json.tool ~/.claude/settings.json

# 2. 重启 Claude Code 以加载新配置
# 直接重新启动 Claude Code 即可

# 3. 发送一条消息测试通知是否正常
# 当 Claude 回复完成后，应该会收到系统通知
```

### 方法二：直接使用

1) 在 Claude Code 的钩子/执行后命令里设置：`python -m vibe_notification`
2) Claude Code 会把当前工具的 JSON（包含 `toolName`）写入 stdin，例如：
   ```bash
   echo '{"toolName": "Task"}' | python -m vibe_notification
   ```
3) VibeNotification 会视为"本轮输出完成"，发送系统通知和声音提醒，标题类似"claude-code — 会话结束"。

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

## Codex：直接传事件
- 将 Codex 事件 JSON 作为参数传入即可触发通知（最小集成）：
  ```bash
  python -m vibe_notification '{"type": "agent-turn-complete", "agent": "codex", "message": "生成完成", "summary": "Codex 本轮结束"}'
  ```
- 事件包含 `conversation_end`/`is_last_turn`/`finish_reason=stop` 等标记时，会默认走“会话结束”通知并播放声音。

## Codex 集成：配置步骤
如果希望在 Codex CLI/脚本里对每次本轮结束自动通知，可按需选择：
- **方案 A（官方 Hook，推荐）**：在 Codex `~/.codex/config.toml` 里配置 `notify`，让 Codex 在每次 `agent-turn-complete` 时调用 VibeNotification。  
  1) 打开 `~/.codex/config.toml`，添加（或合并）：
     ```toml
     # Codex 通知钩子：将事件 JSON 传给 VibeNotification
     notify = ["python", "-m", "vibe_notification"]
     ```
     Codex 会把通知事件作为**单个 JSON 字符串参数**传入（位于最后一个 argv）；`vibe_notification` 的 Codex 解析器已兼容这种调用方式。  
  2) 若想禁用声音（如深夜），在调用前导出：`export VIBE_NOTIFICATION_SOUND=0`。  
  3) 想用自定义 Python/虚拟环境，改为完整可执行路径，如：`notify = ["/Users/me/.venv/bin/python", "-m", "vibe_notification"]`。
- **方案 B（零侵入监听）**：直接运行监听模式，不改 Codex 配置  
  `python -m vibe_notification --watch-codex-history --poll-interval 1.5 --history-path ~/.codex/history.jsonl`  
  只要 Codex 继续写入 history，就能自动检测“turn complete”并通知。

## 监听模式：自动监控历史文件
- 适合不方便写钩子时使用，持续监听 `~/.claude/history.jsonl`，模型每轮输出结束都会通知。
- Claude Code 名义：
  ```bash
  python -m vibe_notification --watch-claude-history --poll-interval 1.5
  ```
- Codex 名义（同一文件，但通知中的 agent 为 codex）：
  ```bash
  python -m vibe_notification --watch-codex-history --poll-interval 1.5
  ```
- 可通过 `--history-path /custom/path/history.jsonl` 指定历史文件位置。

## 故障排除

### Claude Code 钩子不生效？

1. **检查配置文件格式**：
   ```bash
   # 验证 JSON 格式是否正确
   python -m json.tool ~/.claude/config.json
   ```

2. **确认 Python 路径**：
   ```bash
   # 查看当前使用的 Python 路径
   which python

   # 如果使用虚拟环境，需要完整路径
   which python  # 在激活的虚拟环境中执行
   ```

3. **手动测试钩子**：
   ```bash
   # 模拟 Claude Code 传递的数据
   echo '{"toolName": "Read"}' | python -m vibe_notification
   ```

4. **查看 Claude Code 日志**：
   ```bash
   # Claude Code 日志位置
   ~/.claude/logs/
   ```

### 通知不显示？

1. **macOS 权限设置**：
   - 系统偏好设置 → 安全性与隐私 → 通知 → 允许终端/你的终端应用发送通知

2. **安装 terminal-notifier**（推荐）：
   ```bash
   brew install terminal-notifier
   ```

3. **测试系统通知**：
   ```bash
   # 直接测试通知功能
   python -m vibe_notification --test
   ```

## 小贴士
- macOS 建议安装 `terminal-notifier` 以确保弹窗稳定：`brew install terminal-notifier`（未安装会回退 AppleScript，部分环境可能被系统权限阻挡）
- 日志会写入仓库根目录的 `vibe_notification.log`，排查问题时可查看。
- 使用虚拟环境时，记得在配置文件中使用完整的 Python 解释器路径。
