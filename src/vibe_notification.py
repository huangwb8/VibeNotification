#!/usr/bin/env python3
"""
VibeNotification - 为 Claude Code 和 Codex 提供智能会话结束通知

主要功能：
1. 检测 Claude Code 和 Codex 的会话结束事件
2. 跨平台系统通知（macOS、Linux、Windows）
3. 智能声音提示
4. 可配置的通知行为
5. 详细的日志记录

使用方式：
- 作为 Claude Code 钩子：配置 PostToolUse 钩子
- 作为 Codex 钩子：配置 agent-turn-complete 事件处理器
- 独立运行：用于测试和调试
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class NotificationLevel(Enum):
    """通知级别"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class PlatformType(Enum):
    """平台类型"""
    MACOS = "darwin"
    LINUX = "linux"
    WINDOWS = "windows"
    UNKNOWN = "unknown"


@dataclass
class NotificationConfig:
    """通知配置"""
    enable_sound: bool = True
    enable_notification: bool = True
    notification_timeout: int = 10000  # 毫秒
    sound_type: str = "default"
    log_level: str = "INFO"
    detect_conversation_end: bool = True


@dataclass
class NotificationEvent:
    """通知事件"""
    type: str
    agent: str
    message: str
    summary: str
    timestamp: str
    is_last_turn: bool = False
    tool_name: Optional[str] = None
    conversation_end: bool = False
    metadata: Optional[Dict[str, Any]] = None


class VibeNotifier:
    """VibeNotification 核心类"""

    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or NotificationConfig()
        self.platform = self._detect_platform()
        self._setup_logging()

    def _setup_logging(self):
        """设置日志"""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stderr),
                logging.FileHandler('vibe_notification.log')
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _detect_platform(self) -> PlatformType:
        """检测当前平台"""
        system = platform.system().lower()
        if system == "darwin":
            return PlatformType.MACOS
        elif system == "linux":
            return PlatformType.LINUX
        elif system == "windows":
            return PlatformType.WINDOWS
        else:
            return PlatformType.UNKNOWN

    def _shutil_which(self, cmd: str) -> bool:
        """检查命令是否在 PATH 中"""
        try:
            return shutil.which(cmd) is not None
        except Exception:
            return False

    def play_sound(self, sound_type: Optional[str] = None):
        """播放通知声音"""
        if not self.config.enable_sound:
            return

        sound_type = sound_type or self.config.sound_type
        self.logger.debug(f"播放声音: {sound_type}")

        try:
            if self.platform == PlatformType.MACOS:
                self._play_sound_macos(sound_type)
            elif self.platform == PlatformType.LINUX:
                self._play_sound_linux(sound_type)
            elif self.platform == PlatformType.WINDOWS:
                self._play_sound_windows(sound_type)
        except Exception as e:
            self.logger.warning(f"播放声音失败: {e}")

    def _play_sound_macos(self, sound_type: str):
        """macOS 播放声音"""
        if sound_type == "default":
            sound_path = "/System/Library/Sounds/Glass.aiff"
            if os.path.exists(sound_path) and self._shutil_which("afplay"):
                subprocess.Popen(["afplay", sound_path])
                return

        if self._shutil_which("say"):
            subprocess.Popen(["say", "会话完成"])

    def _play_sound_linux(self, sound_type: str):
        """Linux 播放声音"""
        # 尝试播放系统声音
        if self._shutil_which("paplay") and os.path.exists("/usr/share/sounds/freedesktop/stereo/complete.oga"):
            subprocess.Popen(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"])
            return

        # 尝试 TTS
        if self._shutil_which("espeak"):
            subprocess.Popen(["espeak", "会话完成"])
        elif self._shutil_which("spd-say"):
            subprocess.Popen(["spd-say", "会话完成"])

    def _play_sound_windows(self, sound_type: str):
        """Windows 播放声音"""
        # 使用 PowerShell SAPI
        ps = 'Add-Type –AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak("会话完成");'
        subprocess.Popen(["powershell", "-NoProfile", "-Command", ps])

    def show_notification(self, title: str, message: str, subtitle: str = "", level: NotificationLevel = NotificationLevel.INFO):
        """显示系统通知"""
        if not self.config.enable_notification:
            return

        self.logger.debug(f"显示通知: {title} - {message}")

        try:
            if self.platform == PlatformType.MACOS:
                self._show_notification_macos(title, message, subtitle, level)
            elif self.platform == PlatformType.LINUX:
                self._show_notification_linux(title, message, level)
            elif self.platform == PlatformType.WINDOWS:
                self._show_notification_windows(title, message, level)
        except Exception as e:
            self.logger.warning(f"显示通知失败: {e}")
            # 回退到打印
            print(f"[VibeNotification] {title}: {message}", file=sys.stderr)

    def _show_notification_macos(self, title: str, message: str, subtitle: str, level: NotificationLevel):
        """macOS 显示通知"""
        esc_msg = message.replace("\\", "\\\\").replace('"', '\\"')
        esc_title = title.replace("\\", "\\\\").replace('"', '\\"')
        esc_sub = subtitle.replace("\\", "\\\\").replace('"', '\\"')

        script = f'display notification "{esc_msg}" with title "{esc_title}"'
        if esc_sub:
            script += f' subtitle "{esc_sub}"'
        script += ' sound name "Glass"'

        subprocess.Popen(["osascript", "-e", script])

    def _show_notification_linux(self, title: str, message: str, level: NotificationLevel):
        """Linux 显示通知"""
        # 尝试 notify-send
        if self._shutil_which("notify-send"):
            urgency = "normal"
            if level == NotificationLevel.ERROR:
                urgency = "critical"
            elif level == NotificationLevel.WARNING:
                urgency = "normal"

            subprocess.Popen(["notify-send", title, message, "-u", urgency, "-t", str(self.config.notification_timeout)])
            return

        # 尝试 Python DBus
        try:
            from gi.repository import Notify  # type: ignore
            Notify.init("VibeNotification")
            n = Notify.Notification.new(title, message, None)
            n.set_timeout(self.config.notification_timeout)
            n.show()
        except Exception:
            pass

    def _show_notification_windows(self, title: str, message: str, level: NotificationLevel):
        """Windows 显示通知"""
        esc_title = title.replace("'", "''")
        esc_message = message.replace("'", "''")

        # 选择图标
        icon = "Information"
        if level == NotificationLevel.ERROR:
            icon = "Error"
        elif level == NotificationLevel.WARNING:
            icon = "Warning"
        elif level == NotificationLevel.SUCCESS:
            icon = "Information"

        ps_script = (
            "$title = '{t}'; $msg = '{m}'; "
            "[void][Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); "
            "[void][Reflection.Assembly]::LoadWithPartialName('System.Drawing'); "
            "$notify = New-Object System.Windows.Forms.NotifyIcon; "
            "$notify.Icon = [System.Drawing.SystemIcons]::{icon}; "
            "$notify.BalloonTipTitle = $title; "
            "$notify.BalloonTipText = $msg; "
            "$notify.Visible = $true; "
            "$notify.ShowBalloonTip({timeout}); "
            "Start-Sleep -Seconds 6; "
            "$notify.Dispose();"
        ).format(t=esc_title, m=esc_message, icon=icon, timeout=self.config.notification_timeout)

        subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_script])

    def is_claude_code_hook(self) -> bool:
        """检测是否在 Claude Code 钩子上下文中"""
        # 检查 stdin 是否有数据
        if not sys.stdin.isatty():
            return True

        # 检查环境变量
        if os.environ.get("CLAUDE_HOOK_COMMAND") or os.environ.get("CLAUDE_HOOK_TOOL_NAME"):
            return True

        return False

    def parse_claude_code_event(self) -> NotificationEvent:
        """解析 Claude Code 钩子事件"""
        try:
            if not sys.stdin.isatty():
                hook_input = sys.stdin.read()
                if hook_input:
                    hook_data = json.loads(hook_input)
                    tool_name = hook_data.get("toolName", "unknown")

                    # 检测是否是会话结束
                    conversation_end = self._detect_conversation_end_from_hook(hook_data)

                    event = NotificationEvent(
                        type="agent-turn-complete",
                        agent="claude-code",
                        message=f"使用工具: {tool_name}",
                        summary=f"Claude Code 完成了 {tool_name} 操作",
                        timestamp=datetime.now().isoformat(),
                        tool_name=tool_name,
                        conversation_end=conversation_end,
                        is_last_turn=conversation_end,
                        metadata=hook_data
                    )
                    return event
        except Exception as e:
            self.logger.error(f"解析 Claude Code 事件失败: {e}")

        # 回退事件
        return NotificationEvent(
            type="agent-turn-complete",
            agent="claude-code",
            message="Claude Code 操作完成",
            summary="Claude Code 操作完成",
            timestamp=datetime.now().isoformat(),
            conversation_end=False,
            is_last_turn=False
        )

    def _detect_conversation_end_from_hook(self, hook_data: Dict[str, Any]) -> bool:
        """从钩子数据检测会话结束"""
        # 这里可以添加更智能的检测逻辑
        # 例如：检测特定的工具序列或模式
        tool_name = hook_data.get("toolName", "")

        # 如果使用了某些特定的"结束"工具
        end_tools = ["ExitPlanMode", "Skill", "Task"]
        if tool_name in end_tools:
            return True

        # 检查是否有结束标志
        if hook_data.get("conversation_end") or hook_data.get("is_last_turn"):
            return True

        return False

    def parse_codex_event(self, event_json: str) -> NotificationEvent:
        """解析 Codex 事件"""
        try:
            event_data = json.loads(event_json)

            # 检测会话结束
            conversation_end = self._detect_conversation_end(event_data)

            event = NotificationEvent(
                type=event_data.get("type", "unknown"),
                agent=event_data.get("agent", "unknown"),
                message=event_data.get("message", ""),
                summary=event_data.get("summary", ""),
                timestamp=event_data.get("timestamp", datetime.now().isoformat()),
                tool_name=event_data.get("tool_name"),
                conversation_end=conversation_end,
                is_last_turn=conversation_end,
                metadata=event_data
            )
            return event
        except Exception as e:
            self.logger.error(f"解析 Codex 事件失败: {e}")

        # 回退事件
        return NotificationEvent(
            type="unknown",
            agent="unknown",
            message="未知事件",
            summary="未知事件",
            timestamp=datetime.now().isoformat(),
            conversation_end=False,
            is_last_turn=False
        )

    def _detect_conversation_end(self, event: Dict[str, Any]) -> bool:
        """检测会话是否结束"""
        if not isinstance(event, dict):
            return False

        # 直接布尔标志
        for key in ("is_last_turn", "conversation_end", "conversation_finished", "final", "closed"):
            if key in event and bool(event.get(key)):
                return True

        # 检查嵌套字典
        for container_key in ("payload", "metadata", "data", "details"):
            sub = event.get(container_key)
            if isinstance(sub, dict):
                for key in ("conversation_end", "conversation_finished", "is_last_turn", "final"):
                    if key in sub and bool(sub.get(key)):
                        return True

        # 状态字符串
        state = event.get("conversation_state") or event.get("state")
        if isinstance(state, str):
            if state.lower() in ("finished", "ended", "closed", "complete"):
                return True

        # turn/total 启发式
        try:
            turn = event.get("turn")
            total = event.get("total_turns") or event.get("turns_total") or event.get("total_turns_estimate")
            if isinstance(turn, int) and isinstance(total, int) and turn >= total:
                return True
        except Exception:
            pass

        return False

    def build_notification_content(self, event: NotificationEvent) -> Tuple[str, str, str, NotificationLevel]:
        """构建通知内容"""
        if event.conversation_end:
            title = f"{event.agent} — 会话结束"
            message = event.summary or event.message or "会话已结束"
            subtitle = f"工具: {event.tool_name}" if event.tool_name else event.agent
            level = NotificationLevel.SUCCESS
        else:
            title = f"{event.agent} — 操作完成"
            message = event.message or event.summary or "操作已完成"
            subtitle = f"工具: {event.tool_name}" if event.tool_name else event.agent
            level = NotificationLevel.INFO

        # 截断过长的消息
        if len(message) > 240:
            message = message[:236] + "..."

        return title, message, subtitle, level

    def process_event(self, event: NotificationEvent):
        """处理事件并发送通知"""
        self.logger.info(f"处理事件: {event.agent} - {event.type} - 会话结束: {event.conversation_end}")

        # 构建通知内容
        title, message, subtitle, level = self.build_notification_content(event)

        # 播放声音
        self.play_sound()

        # 显示通知
        self.show_notification(title, message, subtitle, level)

        # 记录到日志
        self.logger.info(f"已发送通知: {title} - {message}")

    def run(self):
        """主运行方法"""
        self.logger.info("VibeNotification 启动")

        event = None

        # 检测运行模式
        if self.is_claude_code_hook():
            self.logger.info("检测到 Claude Code 钩子模式")
            event = self.parse_claude_code_event()
        elif len(sys.argv) == 2:
            self.logger.info("检测到 Codex 模式")
            event = self.parse_codex_event(sys.argv[1])
        else:
            self.logger.warning("未知运行模式，使用测试事件")
            event = NotificationEvent(
                type="test",
                agent="vibe-notification",
                message="测试通知",
                summary="VibeNotification 测试运行",
                timestamp=datetime.now().isoformat(),
                conversation_end=True,
                is_last_turn=True
            )

        # 处理事件
        if event:
            self.process_event(event)

        self.logger.info("VibeNotification 完成")


def main():
    """主函数"""
    # 读取配置文件（如果存在）
    config = NotificationConfig()

    # 创建通知器
    notifier = VibeNotifier(config)

    # 运行
    notifier.run()


if __name__ == "__main__":
    main()