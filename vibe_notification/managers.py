"""
管理器模块

负责管理解析器、通知器等组件
"""

from typing import List, Optional, Dict, Any
import logging
from .models import NotificationConfig, NotificationEvent, NotificationLevel
from .parsers import BaseParser, ClaudeCodeParser, CodexParser
from .notifiers import BaseNotifier, SoundNotifier, SystemNotifier
from .adapters import PlatformAdapter, CommandExecutor, DefaultCommandExecutor, create_platform_adapter
from .exceptions import NotifierError


class ParserManager:
    """解析器管理器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.parsers: List[BaseParser] = []
        self._initialize_parsers()

    def _initialize_parsers(self):
        """初始化所有解析器"""
        self.parsers = [
            CodexParser(),
            ClaudeCodeParser(),
        ]
        self.logger.info(f"Initialized {len(self.parsers)} parsers")

    def get_available_parser(self) -> Optional[BaseParser]:
        """获取当前可用的解析器"""
        for parser in self.parsers:
            if parser.can_parse():
                self.logger.debug(f"Using parser: {parser.__class__.__name__}")
                return parser
        self.logger.warning("No suitable parser found")
        return None

    def add_parser(self, parser: BaseParser):
        """添加新的解析器"""
        self.parsers.append(parser)
        self.logger.info(f"Added parser: {parser.__class__.__name__}")

    def remove_parser(self, parser_type: type):
        """移除指定类型的解析器"""
        self.parsers = [p for p in self.parsers if not isinstance(p, parser_type)]
        self.logger.info(f"Removed parsers of type: {parser_type.__name__}")

    def list_parsers(self) -> List[str]:
        """列出所有解析器"""
        return [parser.__class__.__name__ for parser in self.parsers]


class NotifierManager:
    """通知器管理器"""

    def __init__(self, config: NotificationConfig, platform_adapter: PlatformAdapter):
        self.config = config
        self.platform_adapter = platform_adapter
        self.logger = logging.getLogger(__name__)
        self.notifiers: List[BaseNotifier] = []
        self._initialize_notifiers()

    def _initialize_notifiers(self):
        """初始化所有通知器"""
        self.notifiers = [
            SoundNotifier(self.config, self.platform_adapter),
            SystemNotifier(self.config, self.platform_adapter),
        ]
        self.logger.info(f"Initialized {len(self.notifiers)} notifiers")

    def send_notifications(self, title: str, message: str, level: NotificationLevel, subtitle: str = ""):
        """发送通知到所有启用的通知器"""
        successful = 0
        failed = 0

        for notifier in self.notifiers:
            if notifier.is_enabled():
                try:
                    notifier.notify(title, message, level, subtitle=subtitle)
                    successful += 1
                    self.logger.debug(f"Notification sent via {notifier.__class__.__name__}")
                except Exception as e:
                    failed += 1
                    self.logger.warning(f"Notifier {notifier.__class__.__name__} failed: {e}")
                    raise NotifierError(f"Failed to send notification via {notifier.__class__.__name__}: {e}")
            else:
                self.logger.debug(f"Notifier {notifier.__class__.__name__} is disabled")

        self.logger.info(f"Notifications sent: {successful} successful, {failed} failed")

    def add_notifier(self, notifier: BaseNotifier):
        """添加新的通知器"""
        self.notifiers.append(notifier)
        self.logger.info(f"Added notifier: {notifier.__class__.__name__}")

    def remove_notifier(self, notifier_type: type):
        """移除指定类型的通知器"""
        self.notifiers = [n for n in self.notifiers if not isinstance(n, notifier_type)]
        self.logger.info(f"Removed notifiers of type: {notifier_type.__name__}")

    def list_notifiers(self) -> List[str]:
        """列出所有通知器"""
        return [notifier.__class__.__name__ for notifier in self.notifiers]

    def get_enabled_notifiers(self) -> List[str]:
        """获取启用的通知器列表"""
        return [n.__class__.__name__ for n in self.notifiers if n.is_enabled()]


class NotificationBuilder:
    """通知内容构建器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def build_notification_content(
        self,
        event: NotificationEvent,
        custom_title: Optional[str] = None,
        custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """构建通知内容"""
        # 根据事件类型决定通知级别
        if event.conversation_end:
            level = NotificationLevel.SUCCESS
            default_title = f"{event.agent} — 会话结束"
        else:
            level = NotificationLevel.INFO
            default_title = f"{event.agent} — 操作完成"

        # 使用自定义内容或默认内容
        title = custom_title or default_title

        if custom_message:
            message = custom_message
        else:
            message = (
                event.summary or
                event.message or
                ("会话已结束" if event.conversation_end else "操作已完成")
            )

        subtitle = f"工具: {event.tool_name}" if event.tool_name else event.agent

        # 截断过长的消息
        from .utils import truncate_text
        message = truncate_text(message, 240)

        content = {
            "title": title,
            "message": message,
            "subtitle": subtitle,
            "level": level
        }

        self.logger.debug(f"Built notification content: {content}")
        return content

    def build_error_notification(
        self,
        error: Exception,
        context: str = ""
    ) -> Dict[str, Any]:
        """构建错误通知内容"""
        title = "VibeNotification — 错误"
        message = f"{context}: {str(error)}" if context else str(error)
        subtitle = "请检查配置或日志"

        content = {
            "title": title,
            "message": message,
            "subtitle": subtitle,
            "level": NotificationLevel.ERROR
        }

        self.logger.debug(f"Built error notification: {content}")
        return content