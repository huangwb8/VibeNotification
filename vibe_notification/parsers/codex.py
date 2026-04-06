"""
Codex 解析器

解析 Codex 事件
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from .base import BaseParser
from ._stdin import get_stdin_json
from ..models import NotificationEvent
from ..detectors.conversation import detect_conversation_end


class CodexParser(BaseParser):
    """Codex 解析器"""

    DEBUG_CAPTURE_PATH = Path.home() / ".config" / "vibe-notification" / "debug" / "codex-events.jsonl"

    CODEX_HOOK_EVENT_TYPES = {
        "sessionstart": "session-start",
        "userpromptsubmit": "user-prompt-submit",
        "pretooluse": "pre-tool-use",
        "posttooluse": "post-tool-use",
        "stop": "stop-hook",
    }

    def _load_event_data(self) -> Optional[Dict[str, Any]]:
        """读取并校验事件数据。

        支持两种来源：
        1. Codex notify: JSON 作为最后一个 argv 参数传入
        2. Codex hooks.json / stdin: 数据通过 stdin 传入（共享缓存，仅读一次）
        """
        # 优先尝试 argv（notify 机制）
        if len(sys.argv) >= 2:
            try:
                event_data = json.loads(sys.argv[-1])
                if isinstance(event_data, dict):
                    return event_data
            except Exception:
                pass

        # 使用共享 stdin 缓存（避免重复读取导致数据丢失）
        stdin_json = get_stdin_json()
        if isinstance(stdin_json, dict):
            return stdin_json

        return None

    def _get_value(self, event_data: Dict[str, Any], *keys: str) -> Any:
        """兼容 kebab-case / snake_case 的字段读取。"""
        for key in keys:
            if key in event_data:
                return event_data.get(key)
        return None

    def _normalize_hook_event_name(self, event_data: Dict[str, Any]) -> str:
        """标准化 hook 事件名。"""
        value = self._get_value(event_data, "hook_event_name", "hookEventName")
        if not isinstance(value, str):
            return ""
        return value.strip().lower()

    def _iter_nested_dicts(self, value: Any):
        """递归遍历嵌套字典，兼容新版 app-server 负载。"""
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from self._iter_nested_dicts(child)
        elif isinstance(value, list):
            for child in value:
                yield from self._iter_nested_dicts(child)

    def _normalize_phase(self, value: Any) -> str:
        """标准化 phase 字段。"""
        if not isinstance(value, str):
            return ""
        return value.replace("_", "-").strip().lower()

    def _extract_structured_message(self, event_data: Dict[str, Any]) -> str:
        """从新版 Codex 结构化事件中提取更可靠的最终消息。"""
        final_messages = []
        commentary_messages = []
        plan_messages = []

        for payload in self._iter_nested_dicts(event_data):
            for key in ("agentMessage", "agent_message"):
                nested = payload.get(key)
                if not isinstance(nested, dict):
                    continue
                value = nested.get("text")
                if not isinstance(value, str) or not value.strip():
                    continue

                text = value.strip()
                phase = self._normalize_phase(nested.get("phase"))
                if phase == "final-answer":
                    final_messages.append(text)
                else:
                    commentary_messages.append(text)

        for payload in self._iter_nested_dicts(event_data):
            nested = payload.get("plan")
            if not isinstance(nested, dict):
                continue
            value = nested.get("text")
            if isinstance(value, str) and value.strip():
                plan_messages.append(value.strip())

        if final_messages:
            return final_messages[0]

        if plan_messages:
            return plan_messages[0]

        if commentary_messages:
            return commentary_messages[0]

        return ""

    def _capture_debug_payload(self, event_data: Dict[str, Any]) -> None:
        """在 DEBUG 模式下记录原始 Codex payload，便于排查 provider 差异。"""
        if not self.logger.isEnabledFor(logging.DEBUG):
            return

        try:
            compact_payload = json.dumps(event_data, ensure_ascii=False, sort_keys=True)
            self.logger.debug("Codex raw payload: %s", compact_payload)

            self.DEBUG_CAPTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "captured_at": datetime.now().isoformat(),
                "payload": event_data,
            }
            with self.DEBUG_CAPTURE_PATH.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:
            self.logger.debug("写入 Codex DEBUG payload 失败: %s", exc)

    def _infer_event_type(self, event_data: Dict[str, Any]) -> str:
        """推断事件类型。"""
        hook_event_name = self._normalize_hook_event_name(event_data)
        if hook_event_name in self.CODEX_HOOK_EVENT_TYPES:
            return self.CODEX_HOOK_EVENT_TYPES[hook_event_name]

        method = self._get_value(event_data, "method")
        if isinstance(method, str) and method.strip():
            return method

        event_type = self._get_value(event_data, "type", "event")
        if isinstance(event_type, str) and event_type.strip():
            return event_type

        return "unknown"

    def _infer_agent(self, event_data: Dict[str, Any]) -> str:
        """推断代理名称。"""
        agent = self._get_value(event_data, "agent")
        if isinstance(agent, str) and agent.strip():
            return agent

        hook_event_name = self._normalize_hook_event_name(event_data)
        if hook_event_name:
            return "codex-hook"

        client = self._get_value(event_data, "client")
        if isinstance(client, str) and client.strip():
            return "codex"

        return "codex"

    def _infer_message(self, event_data: Dict[str, Any], conversation_end: bool) -> str:
        """推断通知消息。"""
        assistant_message = self._get_value(
            event_data,
            "last_assistant_message",
            "last-assistant-message",
            "message",
        )
        if isinstance(assistant_message, str) and assistant_message.strip():
            return assistant_message

        structured_message = self._extract_structured_message(event_data)
        if structured_message:
            return structured_message

        hook_event_name = self._normalize_hook_event_name(event_data)
        if hook_event_name == "userpromptsubmit":
            return "Codex 已接收用户指令"
        if hook_event_name == "sessionstart":
            return "Codex 会话已启动"
        if hook_event_name == "pretooluse":
            return "Codex 工具调用前"
        if hook_event_name == "posttooluse":
            return "Codex 工具调用完成"
        if hook_event_name == "stop":
            return "Codex Stop hook 已触发"

        if conversation_end:
            return "Codex 回复完成"

        return "Codex 事件已接收"

    def can_parse(self) -> bool:
        """检查是否可以解析 Codex 事件"""
        event_data = self._load_event_data()
        if event_data is None:
            return False

        # 拒绝 Claude Code 钩子事件（由 ClaudeCodeParser 处理）
        hook_event_name = event_data.get("hook_event_name", "")
        if hook_event_name in {"Stop", "SessionEnd", "SubagentStop"}:
            claude_markers = {"stop_hook_active", "transcript_path", "permission_mode"}
            if claude_markers & event_data.keys():
                return False

        return True

    def parse(self) -> Optional[NotificationEvent]:
        """解析 Codex 事件"""
        try:
            event_data = self._load_event_data()
            if event_data is None:
                return None

            self._capture_debug_payload(event_data)
            conversation_end = detect_conversation_end(event_data)
            agent = self._infer_agent(event_data)
            event_type = self._infer_event_type(event_data)
            message = self._infer_message(event_data, conversation_end)
            summary = message if conversation_end else f"{message}（忽略通知）"

            if not conversation_end and event_type in {"agent-turn-complete", "turn-completed"}:
                self.logger.debug(
                    "Suppressing Codex terminal notification for suspicious payload: type=%s, message=%r",
                    event_type,
                    self._get_value(
                        event_data,
                        "last_assistant_message",
                        "last-assistant-message",
                        "message",
                    ),
                )

            event = NotificationEvent(
                type=event_type,
                agent=agent,
                message=message,
                summary=summary,
                timestamp=event_data.get("timestamp", datetime.now().isoformat()),
                tool_name=self._get_value(event_data, "tool_name", "toolName"),
                conversation_end=conversation_end,
                is_last_turn=conversation_end,
                metadata=event_data
            )
            return event
        except Exception as e:
            self.logger.error(f"解析 Codex 事件失败: {e}")

        # 回退事件
        return self.create_fallback_event("codex", "Codex 操作完成")
