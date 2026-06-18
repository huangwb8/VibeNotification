"""
Claude Code 解析器

解析 Claude Code 钩子事件。
支持两种来源：
1. 环境变量 CLAUDE_HOOK_EVENT（旧版 / 部分场景）
2. stdin JSON 中的 hook_event_name 字段（Claude Code 官方 Stop 钩子）
"""

import json
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .base import BaseParser
from ._stdin import get_stdin_json
from .routing import is_claude_context
from ..models import NotificationEvent

# 分析 transcript 时只读尾部窗口，控制内存与耗时
_TRANSCRIPT_TAIL_LINES = 200


class ClaudeCodeParser(BaseParser):
    """Claude Code 解析器"""

    parser_type = "claude_code"

    # Claude Code 钩子事件名（与 Claude Code 发送的大小写一致）
    HOOK_EVENTS = {"Stop", "SessionEnd", "SubagentStop", "PostToolUse", "PreToolUse", "ToolError"}

    def _detect_conversation_end(self, payload: Dict[str, Any]) -> bool:
        """Claude 专用的会话结束判断，不再依赖 Codex 感知逻辑。"""
        event_type = payload.get("type") or payload.get("event")
        if isinstance(event_type, str):
            normalized = event_type.replace("_", "-").strip().lower()
            if normalized == "session-end":
                return False
            if normalized in {"agent-turn-complete", "turn-complete"}:
                return True
            if "turn" in normalized and "complete" in normalized:
                return True

        for key in ("is_last_turn", "conversation_end", "conversation_finished", "final", "closed"):
            if key in payload and bool(payload.get(key)):
                return True

        for key in ("finish_reason", "stop_reason", "stopReason", "reason"):
            reason = payload.get(key)
            if isinstance(reason, str) and reason.strip().lower() in {"stop", "end", "complete", "completed", "done"}:
                return True

        state = payload.get("conversation_state") or payload.get("state")
        if isinstance(state, str) and state.strip().lower() in {"finished", "ended", "closed", "complete"}:
            return True

        return False

    def _is_intermediate_stop(self, stdin_json: Optional[Dict[str, Any]]) -> bool:
        """判断 Stop 钩子是否处于「中间停止」（Claude 仍会继续），应跳过通知。

        Claude Code 新版在 agentic loop 中（工具调用、子代理）也会触发 Stop 钩子，
        不再仅限于「主代理回复结束」。仅凭 hook_event_name=Stop 已无法区分。

        通过 transcript 真实状态判定：若最后一条 assistant 消息仍在调用工具
        （content 含 tool_use），说明 Claude 还会继续，并非真正的回复结束。

        无 transcript 或读取失败时返回 False（保守通知，避免漏报）。
        """
        if not isinstance(stdin_json, dict):
            return False

        # stop_hook_active=True：Stop 链重复触发（上次 Stop 导致 Claude 继续），跳过避免重复通知
        if stdin_json.get("stop_hook_active") is True:
            return True

        transcript_path = stdin_json.get("transcript_path")
        if not isinstance(transcript_path, str) or not transcript_path:
            return False

        last_assistant = self._read_last_assistant_message(Path(transcript_path))
        if last_assistant is None:
            return False

        return self._assistant_message_has_tool_use(last_assistant)

    def _read_last_assistant_message(self, transcript_path: Path) -> Optional[Dict[str, Any]]:
        """从后往前读取 transcript 中最后一条真实 assistant 消息行。

        跳过元数据行（ai-title/attachment/last-prompt/queue-operation/file-history-snapshot 等），
        只保留 type=assistant 且非 isMeta 的真实对话行。仅读取尾部窗口以控制内存与耗时。
        """
        if not transcript_path.is_file():
            return None

        try:
            with transcript_path.open("r", encoding="utf-8") as fp:
                tail = deque(fp, maxlen=_TRANSCRIPT_TAIL_LINES)
        except (OSError, UnicodeDecodeError) as exc:
            self.logger.debug("读取 transcript 失败: %s (%s)", transcript_path, exc)
            return None

        for line in reversed(tail):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            if obj.get("type") != "assistant":
                continue
            if obj.get("isMeta"):
                continue
            return obj

        return None

    @staticmethod
    def _assistant_message_has_tool_use(assistant_obj: Dict[str, Any]) -> bool:
        """判断 assistant 消息 content 是否包含 tool_use（即仍在调用工具）。"""
        message = assistant_obj.get("message")
        if not isinstance(message, dict):
            return False
        content = message.get("content")
        if isinstance(content, str) or not isinstance(content, list):
            return False
        return any(
            isinstance(item, dict) and item.get("type") == "tool_use"
            for item in content
        )

    def _get_hook_event(self) -> Optional[str]:
        """从环境变量或 stdin JSON 获取钩子事件名。"""
        # 优先检查环境变量
        env_event = os.environ.get("CLAUDE_HOOK_EVENT")
        if env_event:
            return env_event

        # 从 stdin JSON 检查 hook_event_name
        stdin_json = get_stdin_json()
        if isinstance(stdin_json, dict):
            name = stdin_json.get("hook_event_name")
            if name and name in self.HOOK_EVENTS:
                return name

        return None

    def can_parse(self) -> bool:
        """检查是否在 Claude Code 钩子上下文中。"""
        return is_claude_context()

    def _parse_hook_event(self) -> Optional[NotificationEvent]:
        """解析钩子事件（环境变量 + stdin JSON 统一入口）。"""
        hook_event = self._get_hook_event()
        stdin_json = get_stdin_json()

        if hook_event == "Stop":
            # Claude Code 新版在 agentic loop 中（工具调用/子代理）也会触发 Stop。
            # 通过 transcript 判定：仍在调用工具或 stop_hook_active 重复触发 → 中间停止，跳过通知。
            if self._is_intermediate_stop(stdin_json):
                self.logger.info(
                    "Stop hook 处于中间停止状态（Claude 仍会继续或重复触发），跳过通知"
                )
                return NotificationEvent(
                    type="stop-intermediate",
                    agent="claude-code",
                    message="Claude 仍在工作",
                    summary="Claude Code 中间停止（忽略通知）",
                    timestamp=datetime.now().isoformat(),
                    conversation_end=False,
                    is_last_turn=False,
                    metadata={
                        "event": "Stop",
                        "source": "hook",
                        "intermediate": True,
                        "stdin": stdin_json or {},
                    },
                )
            return NotificationEvent(
                type="agent-turn-complete",
                agent="claude-code",
                message="Claude 回复完成",
                summary="Claude Code 已完成回复",
                timestamp=datetime.now().isoformat(),
                conversation_end=True,
                is_last_turn=True,
                metadata={"event": "Stop", "source": "hook", "stdin": stdin_json or {}}
            )

        if hook_event == "SubagentStop":
            return NotificationEvent(
                type="subagent-stop",
                agent="claude-code-subagent",
                message="子代理完成任务",
                summary="Claude Code 子代理已完成（忽略通知）",
                timestamp=datetime.now().isoformat(),
                conversation_end=False,
                is_last_turn=False,
                metadata={"event": "SubagentStop", "source": "hook", "stdin": stdin_json or {}}
            )

        if hook_event == "SessionEnd":
            return NotificationEvent(
                type="session-end",
                agent="claude-code",
                message="Claude 会话结束",
                summary="Claude Code 会话已结束（忽略通知）",
                timestamp=datetime.now().isoformat(),
                conversation_end=False,
                is_last_turn=False,
                metadata={"event": "SessionEnd", "source": "hook", "stdin": stdin_json or {}}
            )

        if hook_event == "PostToolUse":
            tool_name = os.environ.get("CLAUDE_HOOK_TOOL_NAME", "unknown")
            return NotificationEvent(
                type="tool-complete",
                agent="claude-code",
                message=f"工具调用完成: {tool_name}",
                summary=f"已完成 {tool_name} 工具调用",
                timestamp=datetime.now().isoformat(),
                tool_name=tool_name,
                conversation_end=False,
                is_last_turn=False,
                metadata={"event": "PostToolUse", "source": "hook", "tool_name": tool_name}
            )

        if hook_event == "PreToolUse":
            self.logger.debug("工具调用开始，跳过通知: %s", os.environ.get("CLAUDE_HOOK_TOOL_NAME", "unknown"))
            return None

        if hook_event == "ToolError":
            tool_name = os.environ.get("CLAUDE_HOOK_TOOL_NAME", "unknown")
            return NotificationEvent(
                type="tool-error",
                agent="claude-code",
                message=f"工具调用失败: {tool_name}",
                summary=f"{tool_name} 工具调用出现错误",
                timestamp=datetime.now().isoformat(),
                tool_name=tool_name,
                conversation_end=False,
                is_last_turn=False,
                metadata={"event": "ToolError", "source": "hook", "tool_name": tool_name}
            )

        return None

    def _parse_stdin_data(self) -> Optional[NotificationEvent]:
        """解析 stdin JSON 数据（非 hook_event_name 场景的回退）。"""
        stdin_json = get_stdin_json()
        if not isinstance(stdin_json, dict):
            return None

        # 如果已经有 hook_event_name 匹配，跳过（已在 _parse_hook_event 处理）
        if stdin_json.get("hook_event_name") in self.HOOK_EVENTS:
            return None

        tool_name = stdin_json.get("toolName") or stdin_json.get("tool_name")
        conversation_end = self._detect_conversation_end(stdin_json)

        if tool_name:
            message = f"使用工具: {tool_name}"
            summary = f"Claude Code 完成了 {tool_name} 操作"
            event_type = "tool-complete"
        else:
            message = stdin_json.get("message") or "Claude Code 操作完成"
            summary = stdin_json.get("summary") or message
            event_type = "agent-turn-complete" if conversation_end else "operation-complete"

        return NotificationEvent(
            type=event_type,
            agent="claude-code",
            message=message,
            summary=summary,
            timestamp=datetime.now().isoformat(),
            tool_name=tool_name,
            conversation_end=conversation_end,
            is_last_turn=conversation_end,
            metadata={"source": "stdin", "data": stdin_json}
        )

    def parse(self) -> Optional[NotificationEvent]:
        """解析 Claude Code 钩子事件。"""
        # 首先处理钩子事件（环境变量或 stdin hook_event_name）
        event = self._parse_hook_event()
        if event is not None:
            return event

        # 回退到 stdin 数据解析
        event = self._parse_stdin_data()
        if event is not None:
            return event

        # 有钩子上下文但没有具体事件类型，创建回退事件
        if os.environ.get("CLAUDE_HOOK_COMMAND") or os.environ.get("CLAUDE_HOOK_TOOL_NAME"):
            return self.create_fallback_event("claude-code", "Claude Code 操作完成")

        return None
