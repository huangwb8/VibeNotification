#!/usr/bin/env python3
"""
命令行入口模块

提供命令行接口
"""

import sys
import argparse
from typing import Optional
from .core import VibeNotifier
from .models import NotificationConfig
from .config import load_config, save_config


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="VibeNotification - 智能 AI 助手会话结束通知系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 作为 Claude Code 钩子使用
  echo '{"toolName": "Task"}' | python -m vibe_notification

  # 作为 Codex 钩子使用
  python -m vibe_notification '{"type": "agent-turn-complete", "agent": "codex"}'

  # 测试模式
  python -m vibe_notification --test

  # 配置模式
  python -m vibe_notification --config
        """
    )

    parser.add_argument(
        "event_json",
        nargs="?",
        help="Codex 事件 JSON 字符串（可选）"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="测试模式，发送测试通知"
    )

    parser.add_argument(
        "--config",
        action="store_true",
        help="交互式配置模式"
    )

    parser.add_argument(
        "--sound",
        choices=["0", "1"],
        help="启用/禁用声音通知 (0=禁用, 1=启用)"
    )

    parser.add_argument(
        "--notification",
        choices=["0", "1"],
        help="启用/禁用系统通知 (0=禁用, 1=启用)"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="设置日志级别"
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息"
    )

    parser.add_argument(
        "--watch-claude-history",
        action="store_true",
        help="监听 ~/.claude/history.jsonl，检测模型单轮输出结束并发送通知"
    )

    parser.add_argument(
        "--history-path",
        help="自定义 Claude history 路径，默认 ~/.claude/history.jsonl"
    )

    parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="监听模式下的轮询间隔（秒），默认 2.0"
    )

    parser.add_argument(
        "--watch-codex-history",
        action="store_true",
        help="监听 ~/.claude/history.jsonl，检测模型单轮输出结束并以 codex 名义发送通知"
    )

    return parser.parse_args()


def interactive_config() -> None:
    """交互式配置"""
    print("=== VibeNotification 配置 ===")
    config = load_config()

    print(f"当前配置:")
    print(f"  声音通知: {'启用' if config.enable_sound else '禁用'}")
    print(f"  系统通知: {'启用' if config.enable_notification else '禁用'}")
    print(f"  日志级别: {config.log_level}")
    print(f"  通知超时: {config.notification_timeout}ms")
    print(f"  声音类型: {config.sound_type}")

    print("\n是否修改配置？ (y/n): ", end="")
    if input().lower() != 'y':
        return

    print("启用声音通知？ (y/n): ", end="")
    config.enable_sound = input().lower() == 'y'

    print("启用系统通知？ (y/n): ", end="")
    config.enable_notification = input().lower() == 'y'

    print("日志级别 (DEBUG/INFO/WARNING/ERROR) [当前: {config.log_level}]: ", end="")
    level = input().strip()
    if level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
        config.log_level = level

    save_config(config)
    print("配置已保存！")


def update_config_from_args(config: NotificationConfig, args: argparse.Namespace) -> NotificationConfig:
    """从命令行参数更新配置"""
    if args.sound is not None:
        config.enable_sound = args.sound == "1"
    if args.notification is not None:
        config.enable_notification = args.notification == "1"
    if args.log_level is not None:
        config.log_level = args.log_level
    return config


def main() -> None:
    """主函数"""
    args = parse_args()

    # 显示版本
    if args.version:
        from . import __version__
        print(f"VibeNotification v{__version__}")
        return

    # 配置模式
    if args.config:
        interactive_config()
        return

    # 加载配置并应用命令行参数
    config = load_config()
    config = update_config_from_args(config, args)

    # 创建通知器
    notifier = VibeNotifier(config)

    # 监听 Claude history 模式
    if args.watch_claude_history or args.watch_codex_history:
        from pathlib import Path
        from .watchers.claude_history import watch_claude_history

        history_path = Path(args.history_path) if args.history_path else None
        agent_name = "codex" if args.watch_codex_history else "claude-code"
        watch_claude_history(
            notifier,
            history_path=history_path,
            poll_interval=args.poll_interval,
            agent_name=agent_name,
        )
        return

    # 测试模式
    if args.test:
        from .models import NotificationEvent
        from datetime import datetime
        event = NotificationEvent(
            type="test",
            agent="vibe-notification",
            message="测试通知",
            summary="VibeNotification 测试运行",
            timestamp=datetime.now().isoformat(),
            conversation_end=True,
            is_last_turn=True
        )
        notifier.process_event(event)
        return

    # 正常模式
    notifier.run()


if __name__ == "__main__":
    main()
