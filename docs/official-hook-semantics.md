# Official Hook Semantics for Reply Completion

查证日期：2026-07-04

本文记录 VibeNotification 对 Claude Code 与 Codex “回复结束通知”的判定依据。目标是明确：通知应绑定到“主代理某一轮回复结束”，而不是整个会话退出，也不是子代理完成。

## 结论

- Claude Code：主回复结束对应 `Stop`。`SubagentStop` 只表示子代理完成响应；`SessionEnd` 是会话生命周期事件，不应作为“本轮回复完成”通知依据。
- Codex：`notify` 当前面向 `agent-turn-complete` 这类 turn 完成事件。Codex Hooks 里 `Stop` 与 `SubagentStop` 是不同事件；`SubagentStop` 是子代理生命周期事件，不应触发主任务完成通知。
- VibeNotification 的默认策略应是：只对主代理回复完成发送通知；显式子代理事件、子代理 transcript、sidechain、`agent_id` / `agent_type` / `agent_transcript_path` 等子代理信号都应被压制。

## 官方依据

### Codex

来源：

- OpenAI Codex Advanced Configuration: https://developers.openai.com/codex/config-advanced
- OpenAI Codex Hooks: https://developers.openai.com/codex/hooks

关键点：

- `notify` 用于在 Codex 发出支持的事件时运行外部程序。官方当前说明的支持事件是 `agent-turn-complete`。
- `notify` 事件 JSON 包含 `type`、`thread-id`、`turn-id`、`cwd`、`input-messages`、`last-assistant-message` 等字段。
- Codex Hooks 列出 `SessionStart`、`SubagentStart`、`PreToolUse`、`PermissionRequest`、`PostToolUse`、`PreCompact`、`PostCompact`、`UserPromptSubmit`、`SubagentStop`、`Stop` 等 hook。
- `SubagentStop` 明确是子代理停止事件，额外字段包括 `turn_id`、`agent_id`、`agent_type`、`agent_transcript_path`、`stop_hook_active`、`last_assistant_message`。
- `Stop` 是 turn 级停止事件，额外字段包括 `turn_id`、`stop_hook_active`、`last_assistant_message`。

对本项目的含义：

- Codex `notify` 的 `agent-turn-complete` 可以作为主回复完成候选事件。
- Codex hook payload 中的 `SubagentStop` 必须被识别为非主回复完成。
- 如果误把 VibeNotification 接到 Codex hooks，`Stop` 也要谨慎处理；hook 事件不等同于 `notify` 的最终通知语义。

### Claude Code

来源：

- Anthropic Claude Code Hooks reference: https://docs.anthropic.com/en/docs/claude-code/hooks

关键点：

- `Stop` 在主 Claude Code agent 完成响应时运行；用户中断导致的停止不触发 `Stop`，API 错误触发 `StopFailure`。
- `Stop` 输入包含 `stop_hook_active`、`last_assistant_message`、`background_tasks`、`session_crons` 等字段。
- `SubagentStop` 在 Claude Code 子代理完成响应时运行。
- `SubagentStop` 输入包含 `stop_hook_active`、`agent_id`、`agent_type`、`agent_transcript_path`、`last_assistant_message`。其中 `transcript_path` 是主会话 transcript，`agent_transcript_path` 是子代理自己的 transcript。
- `Stop` 与 `SubagentStop` 可使用类似的 decision control，但语义不同：一个面向主代理停止，一个面向子代理停止。

对本项目的含义：

- Claude Code 推荐接 `Stop`，因为用户需要的是“某个主回复结束就通知”。
- `SubagentStop` 必须静默跳过，不能提示用户“任务完成”。
- 即使事件名是 `Stop`，如果 transcript 或 payload 明确指向 sidechain / subagent，也应视为非主回复完成。
- `SessionEnd` 不是本轮回复完成，不应作为默认通知触发点。

## 实现映射

当前相关实现：

- `vibe_notification/parsers/routing.py`
  - 识别 Codex 官方 hook 事件名，包括 `SubagentStart` / `SubagentStop`。
  - 区分 Codex 与 Claude Code 同名 hook payload，避免误路由。
- `vibe_notification/parsers/codex.py`
  - 将 Codex `SubagentStop` 解析为 `subagent-stop`。
  - 该事件保持 `conversation_end=False`，由通知层跳过。
- `vibe_notification/detectors/conversation.py`
  - 在 Codex 终态判定前先检查子代理信号。
  - 子代理信号包括 `subagent_id`、`sub_agent`、`agent_id`、`agent_type`、`agent_transcript_path`、`isSubagent`、`isSidechain` 等。
- `vibe_notification/parsers/claude_code.py`
  - `SubagentStop` 明确返回非终态事件。
  - `Stop` 会检查 `stop_hook_active`、工具调用、sidechain/subagent 标记，避免把中间事件或子代理事件当作主回复完成。

## 回归测试

关键测试覆盖：

- `tests/unit/test_parsers_claude_code.py`
  - `test_subagent_stop_event_is_not_main_reply_complete`
  - `test_stop_with_transcript_showing_sidechain_assistant_is_skipped`
  - `test_run_skips_claude_session_end_hook` 相关核心路径
- `tests/unit/test_parsers_codex.py`
  - `test_detect_conversation_end_ignores_codex_subagent_turn_complete`
  - `test_codex_parser_marks_subagent_turn_complete_as_suppressed`
  - `test_codex_parser_suppresses_official_subagent_stop_hook`
- `tests/unit/test_parser_routing.py`
  - `test_detect_parser_type_detects_codex_subagent_stop_from_stdin`

验证命令：

```bash
python -m pytest tests/
```

最近一次验证结果：`181 passed, 2 skipped`。

## 维护原则

- 不把 `SessionEnd` 作为默认通知触发点。
- 不把子代理完成事件作为主任务完成。
- 对官方新增 hook 字段应优先按结构化字段判断，少依赖自由文本。
- 新增 provider 兼容时必须补“主回复完成”和“子代理完成不通知”两类回归测试。
