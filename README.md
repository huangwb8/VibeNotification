# VibeNotification

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-macOS%20|%20Linux%20|%20Windows-lightgrey.svg)](https://github.com/huangwb8/VibeNotification)

**智能 AI 助手会话结束通知系统** - 当 Claude Code 或 Codex 完成“本轮对话输出”时，自动弹出系统通知提醒用户。

## ✨ 特性

- 🎯 **智能检测**：自动检测 Claude Code 和 Codex 的“单轮对话结束”（模型完成一次回复）事件
- 🌍 **跨平台支持**：macOS、Linux、Windows 全平台兼容
- 🔊 **声音提示**：可配置的通知声音
- 🔔 **系统通知**：原生系统通知，支持标题、内容和副标题
- ⚙️ **高度可配置**：通过配置文件自定义通知行为
- 📝 **详细日志**：完整的日志记录，便于调试
- 🤖 **双平台支持**：同时支持 Claude Code 和 Codex 的事件处理

## 📦 安装

### 方法一：直接使用（推荐）

1. 克隆仓库：
```bash
git clone https://github.com/huangwb8/VibeNotification.git
cd VibeNotification
```

2. 确保 Python 3.7+ 已安装：
```bash
python --version
```

3. 安装依赖（可选）：
```bash
# 对于 Linux 用户，可能需要安装通知依赖
# Ubuntu/Debian
sudo apt-get install libnotify-bin espeak

# Fedora
sudo dnf install libnotify espeak

# 对于 Windows 用户，确保 Python 已添加到 PATH
# 对于 macOS 用户，系统通知已内置
```

### 方法二：作为模块安装

```bash
pip install -e .
```

### 方法三：使用 pip 安装

```bash
# 从 GitHub 安装
pip install git+https://github.com/huangwb8/VibeNotification.git

# 或从本地安装
pip install /path/to/VibeNotification
```

## 🚀 快速开始

### 会话结束语义说明

- “会话结束”指的是**模型完成当前这一轮完整输出**（例如用户输入 `hello`，模型回复 `how are you?`，回复结束即视为会话结束）
- 不需要 `/exit` 或手动发送退出命令；VibeNotification 会在检测到模型的“turn complete / agent-turn-complete / assistant 完整消息”时发送通知
- 若事件中有 `conversation_end`、`is_last_turn` 等标记，也会被识别

### 方案一：在 Codex `config.toml` 中注册钩子

1. 打开 Codex 配置文件（Codex CLI 默认 `~/.codex/config.toml`）。
2. 在 hooks 段落追加一条“单轮结束”钩子，确保事件 JSON 作为参数传给 VibeNotification：

```toml
# ~/.config/codex/config.toml
[hooks]
# Codex 在每次 agent 完成输出后执行；{{json}}/{$json} 请替换为 Codex 实际提供的占位符
agent_turn_complete = "python -m vibe_notification '{{json}}'"
# codex resume 019b3b13-9c09-7021-838c-7ca34bb66bc2
```

> 如果你的 Codex 版本使用不同的占位符或字段名，请把 `{{json}}` 换成实际的事件 JSON 变量；保持 `type=agent-turn-complete` 即可被自动识别为会话结束。

### 方案二：在 Claude Code `settings.json` 中注册钩子

1. 根据 Claude Code 文档，配置文件支持全局 `~/.claude/settings.json`，或项目内 `.claude/settings.json`（优先级更高）。可以在 REPL 里输入 `/config` 打开配置界面创建/编辑该文件。
2. 在 `hooks` 段落添加 PostToolUse/PreToolUse 钩子，Claude Code 会把钩子事件 JSON 通过 stdin 传给命令：

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          { "type": "command", "command": "python -m vibe_notification" }
        ]
      }
    ]
  }
}
```

> 如需更精细的匹配，可把 `matcher` 换成具体工具名（如 `Edit|Write`）；如果你的 Claude Code 版本使用不同的钩子键（如 `PreToolUse`/`SessionStart`），请放在对应事件下，命令无需额外参数，stdin 自带 `toolName`、`conversation_end` 等字段。

### 方案三：无需改配置，直接监听历史文件

```bash
# 监听 ~/.claude/history.jsonl（模型每轮输出结束即通知）
python -m vibe_notification --watch-claude-history

# 以 codex 身份通知（同样读取 ~/.claude/history.jsonl）
python -m vibe_notification --watch-codex-history

# 可调节轮询与路径
python -m vibe_notification --watch-claude-history --poll-interval 1.0 --history-path /path/to/history.jsonl
```

### 其它常用命令

```bash
# 发送测试通知
python -m vibe_notification --test

# 直接模拟 Claude/Codex 钩子事件
echo '{"toolName": "Task"}' | python -m vibe_notification
python -m vibe_notification '{"type": "agent-turn-complete", "agent": "codex", "message": "生成完毕"}'
```

#### 模拟 Claude Code 事件
```bash
# 模拟会话结束事件（模型完成一轮输出）
echo '{"toolName": "ExitPlanMode"}' | python -m vibe_notification

# 模拟普通工具事件
echo '{"toolName": "Write", "conversation_end": false}' | python -m vibe_notification
```

#### 模拟 Codex 事件
```bash
# 模拟 Codex 会话结束（省略 conversation_end，类型自动判断）
python -m vibe_notification '{"type": "agent-turn-complete", "agent": "codex", "message": "how are you?"}'

# 模拟 Codex 普通事件
python -m vibe_notification '{"type": "agent-turn-complete", "agent": "codex", "message": "操作完成"}'
```

### 4. 平台特定设置

#### macOS
- ✅ 系统通知：原生支持
- ✅ 声音提示：使用 `afplay` 或 `say` 命令
- ⚙️ 无需额外安装

#### Linux
- ✅ 系统通知：需要 `notify-send` 或 `python3-gi`
- ✅ 声音提示：需要 `paplay`、`espeak` 或 `spd-say`
- 📦 安装依赖：
  ```bash
  # Ubuntu/Debian
  sudo apt-get install libnotify-bin notify-osd espeak
  
  # Fedora
  sudo dnf install libnotify espeak
  
  # Arch Linux
  sudo pacman -S libnotify espeak
  ```

#### Windows
- ✅ 系统通知：使用 PowerShell 和 .NET
- ✅ 声音提示：使用 Windows SAPI 语音合成
- ⚙️ 需要 Python 3.7+ 和 PowerShell 5.1+

### 5. 验证安装

运行以下命令验证安装是否成功：

```bash
# 检查 Python 版本
python --version

# 运行测试套件
python -m pytest tests/

# 检查配置
python -m vibe_notification --config

# 查看帮助
python -m vibe_notification --help
```

### 6. 故障排除

#### 常见问题

**问题：没有收到通知**
- ✅ 检查系统通知设置是否允许 Python 发送通知
- ✅ 检查声音是否启用（系统声音设置）
- ✅ 查看日志文件：`cat vibe_notification.log`

**问题：Linux 上没有声音**
- ✅ 安装 `espeak`：`sudo apt-get install espeak`
- ✅ 或安装 `spd-say`：`sudo apt-get install speech-dispatcher`

**问题：Windows 上 PowerShell 报错**
- ✅ 确保 PowerShell 版本 >= 5.1
- ✅ 以管理员身份运行一次允许脚本执行：`Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

**问题：钩子不工作**
- ✅ 检查钩子配置文件路径是否正确
- ✅ 检查 Python 路径是否正确
- ✅ 查看 Claude Code 日志：`~/.config/claude-code/logs/`

### 7. 下一步

安装并验证成功后：
1. **自定义配置**：运行 `python -m vibe_notification --config` 进行交互式配置
2. **高级用法**：查看 [examples/](examples/) 目录了解更多用法
3. **集成到工作流**：将 VibeNotification 集成到你的自动化工作流中

## ⚙️ 配置

VibeNotification 支持通过配置文件进行自定义。创建 `config.json`：

```json
{
  "enable_sound": true,
  "enable_notification": true,
  "notification_timeout": 10000,
  "sound_type": "default",
  "log_level": "INFO",
  "detect_conversation_end": true
}
```

### 配置选项说明

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enable_sound` | boolean | `true` | 是否播放通知声音 |
| `enable_notification` | boolean | `true` | 是否显示系统通知 |
| `notification_timeout` | integer | `10000` | 通知显示时间（毫秒） |
| `sound_type` | string | `"default"` | 声音类型（平台相关） |
| `log_level` | string | `"INFO"` | 日志级别：DEBUG, INFO, WARNING, ERROR |
| `detect_conversation_end` | boolean | `true` | 是否检测会话结束 |

## 🎨 自定义通知

### 1. 自定义声音

**macOS:**
- 使用系统声音：`/System/Library/Sounds/`
- 自定义声音文件路径

**Linux:**
- 系统声音：`/usr/share/sounds/`
- 支持 `paplay`, `aplay`, `espeak`, `spd-say`

**Windows:**
- 使用系统语音合成（SAPI）

### 2. 自定义通知样式

VibeNotification 支持不同级别的通知：

```python
from vibe_notification import VibeNotifier, NotificationEvent, NotificationLevel
from datetime import datetime

notifier = VibeNotifier()

# 创建自定义事件
event = NotificationEvent(
    type="custom-event",
    agent="my-agent",
    message="自定义消息",
    summary="自定义通知演示",
    timestamp=datetime.now().isoformat(),
    conversation_end=True,
    level=NotificationLevel.SUCCESS  # INFO, SUCCESS, WARNING, ERROR
)

# 发送通知
notifier.process_event(event)
```

## 📁 项目结构

```
VibeNotification/
├── vibe_notification/          # 主包目录
│   ├── __init__.py             # 包导出和版本
│   ├── core.py                 # 核心逻辑和主类
│   ├── models.py               # 数据模型（枚举、数据类）
│   ├── config.py               # 配置管理
│   ├── utils.py                # 工具函数
│   ├── cli.py                  # 命令行入口
│   ├── notifiers/              # 通知器实现
│   │   ├── __init__.py
│   │   ├── base.py             # 通知器基类
│   │   ├── sound.py            # 声音通知器
│   │   └── system.py           # 系统通知器
│   ├── parsers/                # 事件解析器
│   │   ├── __init__.py
│   │   ├── base.py             # 解析器基类
│   │   ├── claude_code.py      # Claude Code 解析器
│   │   └── codex.py            # Codex 解析器
│   └── detectors/              # 检测器
│       ├── __init__.py
│       └── conversation.py     # 会话结束检测器
├── notify.py                   # 向后兼容性入口脚本
├── config.json                 # 配置文件（可选）
├── requirements.txt            # Python 依赖
├── setup.py                    # 安装脚本（向后兼容）
├── pyproject.toml              # 现代构建配置
├── README.md                   # 本文档
├── LICENSE                     # MIT 许可证
├── tests/                      # 测试文件
│   └── test_notification.py    # 测试套件
├── docs/                       # 文档
│   ├── configuration.md
│   └── advanced_usage.md
└── examples/                   # 示例代码
    └── custom_notifier.py      # 自定义通知器示例
```

## 🔧 开发

### 设置开发环境

```bash
# 克隆仓库
git clone https://github.com/huangwb8/VibeNotification.git
cd VibeNotification

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 安装为可编辑模式（使用现代构建）
pip install -e . --use-pep517
```

### 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_notification.py -v

# 带覆盖率报告
pytest --cov=src tests/
```

### 代码风格

项目使用 Black 和 isort 进行代码格式化：

```bash
# 格式化代码
black src/ tests/
isort src/ tests/

# 检查代码质量
flake8 src/ tests/
mypy src/
```

## 📊 日志

VibeNotification 会记录详细日志到 `vibe_notification.log`：

```
2025-12-20 13:00:00,000 - vibe_notification - INFO - VibeNotification 启动
2025-12-20 13:00:00,100 - vibe_notification - INFO - 检测到 Claude Code 钩子模式
2025-12-20 13:00:00,200 - vibe_notification - INFO - 处理事件: claude-code - agent-turn-complete - 会话结束: True
2025-12-20 13:00:00,300 - vibe_notification - INFO - 已发送通知: claude-code — 会话结束 - 使用工具: Write
2025-12-20 13:00:00,400 - vibe_notification - INFO - VibeNotification 完成

2025-12-20 13:05:00,000 - vibe_notification - INFO - VibeNotification 启动
2025-12-20 13:05:00,100 - vibe_notification - INFO - 检测到 Codex 模式
2025-12-20 13:05:00,200 - vibe_notification - INFO - 处理事件: codex - agent-turn-complete - 会话结束: True
2025-12-20 13:05:00,300 - vibe_notification - INFO - 已发送通知: codex — 会话结束 - 成功生成代码文件
2025-12-20 13:05:00,400 - vibe_notification - INFO - VibeNotification 完成
```

## 🤝 贡献

欢迎贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何参与项目。

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

## 📄 许可证

本项目基于 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。
