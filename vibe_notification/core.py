"""
核心模块

整合所有组件，提供主要功能
"""

import sys
import logging
from datetime import datetime
from typing import Optional, Tuple, List
from .models import NotificationConfig, NotificationEvent, NotificationLevel
from .config import get_env_config
from .parsers import ClaudeCodeParser, CodexParser, BaseParser
from .notifiers import SoundNotifier, SystemNotifier
from .utils import truncate_text


class VibeNotifier:
    """VibeNotification 核心类"""

    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or get_env_config()
        self._setup_logging()
        self._setup_parsers()
        self._setup_notifiers()

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

    def _setup_parsers(self):
        """设置解析器"""
        self.parsers: List[BaseParser] = [
            ClaudeCodeParser(),
            CodexParser(),
        ]

    def _setup_notifiers(self):
        """设置通知器"""
        self.notifiers = [
            SoundNotifier(self.config),
            SystemNotifier(self.config),
        ]

    def get_parser(self) -> Optional[BaseParser]:
        """获取合适的解析器"""
        for parser in self.parsers:
            if parser.can_parse():
                return parser
        return None

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
        message = truncate_text(message, 240)

        return title, message, subtitle, level

    def process_event(self, event: NotificationEvent):
        """处理事件并发送通知"""
        self.logger.info(f"处理事件: {event.agent} - {event.type} - 会话结束: {event.conversation_end}")

        # 构建通知内容
        title, message, subtitle, level = self.build_notification_content(event)

        # 发送通知
        for notifier in self.notifiers:
            if notifier.is_enabled():
                try:
                    notifier.notify(title, message, level, subtitle=subtitle)
                except Exception as e:
                    self.logger.warning(f"通知器 {notifier.__class__.__name__} 失败: {e}")

        # 记录到日志
        self.logger.info(f"已发送通知: {title} - {message}")

    def run(self):
        """主运行方法"""
        self.logger.info("VibeNotification 启动")

        # 获取解析器
        parser = self.get_parser()
        if parser:
            event = parser.parse()
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
        self.process_event(event)
        self.logger.info("VibeNotification 完成")