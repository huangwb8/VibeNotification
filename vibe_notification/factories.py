"""
工厂模块

提供创建各种组件的工厂方法
"""

from typing import List, Dict, Any
from .models import NotificationConfig
from .parsers import BaseParser, ClaudeCodeParser, CodexParser
from .notifiers import BaseNotifier, SoundNotifier, SystemNotifier
from .adapters import PlatformAdapter, CommandExecutor, DefaultCommandExecutor, create_platform_adapter


class ParserFactory:
    """解析器工厂"""

    @staticmethod
    def create_default_parsers() -> List[BaseParser]:
        """创建默认的解析器列表"""
        return [
            CodexParser(),
            ClaudeCodeParser(),
        ]

    @staticmethod
    def create_parser(parser_type: str) -> BaseParser:
        """根据类型创建单个解析器"""
        parsers = {
            "claude_code": ClaudeCodeParser,
            "codex": CodexParser,
        }

        parser_class = parsers.get(parser_type.lower())
        if not parser_class:
            raise ValueError(f"Unknown parser type: {parser_type}")

        return parser_class()

    @staticmethod
    def create_custom_parsers(parser_configs: List[Dict[str, Any]]) -> List[BaseParser]:
        """根据配置创建自定义解析器列表"""
        parsers = []
        for config in parser_configs:
            parser_type = config.get("type")
            if not parser_type:
                continue

            parser = ParserFactory.create_parser(parser_type)

            # 如果解析器有配置方法，应用配置
            if hasattr(parser, "configure") and config.get("config"):
                parser.configure(config["config"])

            parsers.append(parser)

        return parsers


class NotifierFactory:
    """通知器工厂"""

    @staticmethod
    def create_default_notifiers(
        config: NotificationConfig,
        platform_adapter: PlatformAdapter
    ) -> List[BaseNotifier]:
        """创建默认的通知器列表"""
        return [
            SoundNotifier(config, platform_adapter),
            SystemNotifier(config, platform_adapter),
        ]

    @staticmethod
    def create_notifier(
        notifier_type: str,
        config: NotificationConfig,
        platform_adapter: PlatformAdapter
    ) -> BaseNotifier:
        """根据类型创建单个通知器"""
        notifiers = {
            "sound": lambda: SoundNotifier(config, platform_adapter),
            "system": lambda: SystemNotifier(config, platform_adapter),
        }

        notifier_factory = notifiers.get(notifier_type.lower())
        if not notifier_factory:
            raise ValueError(f"Unknown notifier type: {notifier_type}")

        return notifier_factory()

    @staticmethod
    def create_custom_notifiers(
        notifier_configs: List[Dict[str, Any]],
        config: NotificationConfig,
        platform_adapter: PlatformAdapter
    ) -> List[BaseNotifier]:
        """根据配置创建自定义通知器列表"""
        notifiers = []
        for config_item in notifier_configs:
            notifier_type = config_item.get("type")
            if not notifier_type:
                continue

            notifier = NotifierFactory.create_notifier(notifier_type, config, platform_adapter)

            # 如果通知器有配置方法，应用配置
            if hasattr(notifier, "configure") and config_item.get("config"):
                notifier.configure(config_item["config"])

            notifiers.append(notifier)

        return notifiers


class AdapterFactory:
    """适配器工厂"""

    @staticmethod
    def create_default_executor() -> CommandExecutor:
        """创建默认的命令执行器"""
        return DefaultCommandExecutor()

    @staticmethod
    def create_platform_adapter(executor: CommandExecutor = None) -> PlatformAdapter:
        """创建平台适配器"""
        if executor is None:
            executor = AdapterFactory.create_default_executor()
        return create_platform_adapter(executor)