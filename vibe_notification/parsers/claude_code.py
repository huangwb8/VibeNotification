"""
Claude Code 解析器

解析 Claude Code 钩子事件。
支持两种来源：
1. 环境变量 CLAUDE_HOOK_EVENT（旧版 / 部分场景）
2. stdin JSON 中的 hook_event_name 字段（Claude Code 官方 Stop 钩子）
"""

import hashlib
import json
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .base import BaseParser
from ._stdin import get_stdin_json
from .routing import is_claude_context
from ..dedupe import mark_recent_key
from ..models import NotificationEvent

# 分析 transcript 时只读尾部窗口，控制内存与耗时
_TRANSCRIPT_TAIL_LINES = 200
CLAUDE_STOP_DEDUPE_STATE_PATH = (
    Path.home() / ".config" / "vibe-notification" / "claude-stop-dedupe.json"
)
CLAUDE_STOP_DEDUPE_TTL_SECONDS = 60
CLAUDE_STABLE_MESSAGE_DEDUPE_TTL_SECONDS = 24 * 60 * 60


class ClaudeCodeParser(BaseParser):
    """Claude Code 解析器"""

    parser_type = "claude_code"

    # Claude Code 钩子事件名（与 Claude Code 发送的大小写一致）
    HOOK_EVENTS = {
        "Stop",
        "SessionEnd",
        "SubagentStop",
        "PostToolUse",
        "PreToolUse",
        "ToolError",
        "Notification",
        "UserPromptSubmit",
        "PreCompact",
        "SessionStart",
    }

    @classmethod
    def _canonical_hook_event(cls, value: Any) -> Optional[str]:
        """将 hook 事件名归一到 Claude Code 官方大小写。"""
        if not isinstance(value, str):
            return None
        normalized = value.replace("_", "").replace("-", "").strip().lower()
        for event_name in cls.HOOK_EVENTS:
            candidate = event_name.replace("_", "").replace("-", "").lower()
            if normalized == candidate:
                return event_name
        return None

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

        新版优先使用 Stop 的结构化字段与 last_assistant_message；仅在旧负载缺少
        最终文本时回退读取 transcript。无 transcript 或读取失败时保守通知。
        """
        if not isinstance(stdin_json, dict):
            return False

        if self._payload_indicates_subagent(stdin_json):
            return True

        # stop_hook_active=True：Stop 链重复触发（上次 Stop 导致 Claude 继续），跳过避免重复通知
        if stdin_json.get("stop_hook_active") is True:
            return True

        # Claude Code 2.1.145+ 会在后台任务/定时任务仍可唤醒当前 turn 时触发 Stop。
        # 这些 Stop 是暂时空闲，不是用户所需的最终回复完成。
        for key in ("background_tasks", "session_crons"):
            pending = stdin_json.get(key)
            if isinstance(pending, (list, dict)) and pending:
                return True

        # 新版 Stop 明确提供最终文本；官方建议通知类 hook 使用此字段，避免读取
        # 可能异步滞后的 transcript。transcript 仅作为旧版本兼容回退。
        last_message = stdin_json.get("last_assistant_message") or stdin_json.get(
            "lastAssistantMessage"
        )
        if isinstance(last_message, str) and last_message.strip():
            return False

        transcript_path = stdin_json.get("transcript_path")
        if not isinstance(transcript_path, str) or not transcript_path:
            return False

        last_assistant = self._read_last_assistant_message(Path(transcript_path))
        if last_assistant is None:
            return False

        return (
            self._assistant_message_has_tool_use(last_assistant)
            or self._assistant_message_is_sidechain(last_assistant)
        )

    def _read_last_assistant_message(self, transcript_path: Path) -> Optional[Dict[str, Any]]:
        """从 transcript 读取最后一条真实 assistant 消息。"""
        record = self._read_last_assistant_message_record(transcript_path)
        if record is None:
            return None
        _, assistant_obj = record
        return assistant_obj

    def _read_last_assistant_message_record(
        self,
        transcript_path: Path,
    ) -> Optional[Tuple[int, Dict[str, Any]]]:
        """从后往前读取 transcript 中最后一条真实 assistant 消息行。

        跳过元数据行（ai-title/attachment/last-prompt/queue-operation/file-history-snapshot 等），
        只保留 type=assistant 且非 isMeta 的真实对话行。返回行号和消息体，用于 Stop 去重。
        仅读取尾部窗口以控制内存与耗时。
        """
        if not transcript_path.is_file():
            return None

        try:
            with transcript_path.open("r", encoding="utf-8") as fp:
                tail = deque(enumerate(fp, start=1), maxlen=_TRANSCRIPT_TAIL_LINES)
        except (OSError, UnicodeDecodeError) as exc:
            self.logger.debug("读取 transcript 失败: %s (%s)", transcript_path, exc)
            return None

        for line_number, line in reversed(tail):
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
            return line_number, obj

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

    @staticmethod
    def _assistant_message_is_sidechain(assistant_obj: Dict[str, Any]) -> bool:
        """判断 assistant 行是否来自 Claude Code 子代理 sidechain。"""
        return any(
            assistant_obj.get(key) is True
            for key in ("isSidechain", "is_sidechain", "sidechain", "isSubagent", "is_subagent")
        )

    @classmethod
    def _payload_indicates_subagent(cls, value: Any) -> bool:
        """递归识别 Stop stdin 中明确的子代理标记。"""
        if isinstance(value, dict):
            for key in ("isSubagent", "is_subagent", "isSidechain", "is_sidechain", "sidechain"):
                if value.get(key) is True:
                    return True

            for key in (
                "subagent",
                "sub_agent",
                "subagent_id",
                "sub_agent_id",
                "subagent_name",
                "sub_agent_name",
            ):
                marker = value.get(key)
                if isinstance(marker, bool):
                    if marker is True:
                        return True
                    continue
                if isinstance(marker, dict) and marker:
                    return True
                if isinstance(marker, (str, int, float)) and str(marker).strip():
                    return True

            for key in ("agent", "role", "source", "event", "hook_event_name", "hookEventName"):
                marker = value.get(key)
                if isinstance(marker, str):
                    normalized = marker.replace("_", "-").strip().lower()
                    if "subagent" in normalized or "sub-agent" in normalized:
                        return True

            return any(cls._payload_indicates_subagent(child) for child in value.values())

        if isinstance(value, list):
            return any(cls._payload_indicates_subagent(child) for child in value)

        return False

    @staticmethod
    def _stable_digest(value: Any) -> str:
        """为去重输入生成稳定短摘要，避免状态文件保存大段回复。"""
        try:
            text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        except TypeError:
            text = str(value)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]

    def _stop_dedupe_key(
        self,
        stdin_json: Optional[Dict[str, Any]],
    ) -> Optional[Tuple[str, float]]:
        """生成最终 Stop 事件的跨进程去重 key 与适用 TTL。

        优先使用 transcript 中稳定的 assistant message.id；无稳定 ID 时按行号区分
        新回复，无 transcript 时短期退化为 last_assistant_message 去重。
        """
        if not isinstance(stdin_json, dict):
            return None

        session_id = stdin_json.get("session_id") or stdin_json.get("sessionId") or ""
        cwd = stdin_json.get("cwd") or ""
        transcript_path = stdin_json.get("transcript_path")

        if isinstance(transcript_path, str) and transcript_path:
            path = Path(transcript_path)
            record = self._read_last_assistant_message_record(path)
            if record is not None:
                line_number, assistant_obj = record
                message = assistant_obj.get("message")
                message_id = message.get("id") if isinstance(message, dict) else None
                if isinstance(message_id, str) and message_id.strip():
                    return (
                        self._stable_digest({
                            "session_id": session_id,
                            "cwd": cwd,
                            "transcript_path": str(path),
                            "assistant_message_id": message_id.strip(),
                        }),
                        CLAUDE_STABLE_MESSAGE_DEDUPE_TTL_SECONDS,
                    )
                return (
                    self._stable_digest({
                        "session_id": session_id,
                        "cwd": cwd,
                        "transcript_path": str(path),
                        "line_number": line_number,
                        "assistant": assistant_obj,
                    }),
                    CLAUDE_STOP_DEDUPE_TTL_SECONDS,
                )

        last_message = stdin_json.get("last_assistant_message") or stdin_json.get(
            "lastAssistantMessage"
        )
        if isinstance(last_message, str) and last_message.strip():
            return (
                self._stable_digest({
                    "session_id": session_id,
                    "cwd": cwd,
                    "last_assistant_message": last_message.strip(),
                }),
                CLAUDE_STOP_DEDUPE_TTL_SECONDS,
            )

        return None

    def _is_duplicate_final_stop(self, stdin_json: Optional[Dict[str, Any]]) -> bool:
        """判断同一条最终 Stop 是否已经通知过。"""
        dedupe_identity = self._stop_dedupe_key(stdin_json)
        if not dedupe_identity:
            return False

        dedupe_key, ttl_seconds = dedupe_identity

        state_path = CLAUDE_STOP_DEDUPE_STATE_PATH
        return mark_recent_key(
            state_path,
            dedupe_key,
            ttl_seconds,
        )

    def _get_raw_hook_event(self) -> Any:
        """读取未归一化 hook 名，用于对未来未知事件 fail-closed。"""
        env_event = os.environ.get("CLAUDE_HOOK_EVENT")
        if env_event:
            return env_event

        stdin_json = get_stdin_json()
        if isinstance(stdin_json, dict):
            return stdin_json.get("hook_event_name")
        return None

    def _get_hook_event(self) -> Optional[str]:
        """从环境变量或 stdin JSON 获取钩子事件名。"""
        return self._canonical_hook_event(self._get_raw_hook_event())

    def can_parse(self) -> bool:
        """检查是否在 Claude Code 钩子上下文中。"""
        return is_claude_context()

    def _parse_hook_event(self) -> Optional[NotificationEvent]:
        """解析钩子事件（环境变量 + stdin JSON 统一入口）。"""
        raw_hook_event = self._get_raw_hook_event()
        hook_event = self._get_hook_event()
        stdin_json = get_stdin_json()

        if raw_hook_event and hook_event is None:
            self.logger.info("未知 Claude hook 事件，安全跳过: %s", raw_hook_event)
            return NotificationEvent(
                type="hook-unsupported",
                agent="claude-code",
                message="Claude Code hook 事件未适配",
                summary="Claude Code 未知 hook（忽略通知）",
                timestamp=datetime.now().isoformat(),
                conversation_end=False,
                is_last_turn=False,
                metadata={
                    "event": str(raw_hook_event),
                    "source": "hook",
                    "suppress_notification": True,
                },
            )

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
                        "suppress_notification": True,
                        "stdin": stdin_json or {},
                    },
                )
            if self._is_duplicate_final_stop(stdin_json):
                self.logger.info("重复 Stop hook 指向同一条 Claude 回复，跳过通知")
                return NotificationEvent(
                    type="stop-duplicate",
                    agent="claude-code",
                    message="Claude 回复已处理",
                    summary="Claude Code 重复 Stop（忽略通知）",
                    timestamp=datetime.now().isoformat(),
                    conversation_end=False,
                    is_last_turn=False,
                    metadata={
                        "event": "Stop",
                        "source": "hook",
                        "duplicate": True,
                        "suppress_notification": True,
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
                metadata={
                    "event": "SubagentStop",
                    "source": "hook",
                    "suppress_notification": True,
                    "stdin": stdin_json or {},
                }
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
                metadata={
                    "event": "SessionEnd",
                    "source": "hook",
                    "suppress_notification": True,
                    "stdin": stdin_json or {},
                }
            )

        if hook_event in {"Notification", "UserPromptSubmit", "PreCompact", "SessionStart"}:
            event_type = {
                "Notification": "notification",
                "UserPromptSubmit": "user-prompt-submit",
                "PreCompact": "pre-compact",
                "SessionStart": "session-start",
            }[hook_event]
            message = "Claude Code hook 事件"
            if isinstance(stdin_json, dict):
                stdin_message = stdin_json.get("message")
                if isinstance(stdin_message, str) and stdin_message.strip():
                    message = stdin_message.strip()

            return NotificationEvent(
                type=event_type,
                agent="claude-code",
                message=message,
                summary=f"Claude Code {hook_event}（忽略通知）",
                timestamp=datetime.now().isoformat(),
                conversation_end=False,
                is_last_turn=False,
                metadata={
                    "event": hook_event,
                    "source": "hook",
                    "suppress_notification": True,
                    "stdin": stdin_json or {},
                },
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
                metadata={
                    "event": "PostToolUse",
                    "source": "hook",
                    "tool_name": tool_name,
                    "suppress_notification": True,
                }
            )

        if hook_event == "PreToolUse":
            self.logger.debug(
                "工具调用开始，跳过通知: %s",
                os.environ.get("CLAUDE_HOOK_TOOL_NAME", "unknown"),
            )
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
                metadata={
                    "event": "ToolError",
                    "source": "hook",
                    "tool_name": tool_name,
                    "suppress_notification": True,
                }
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
