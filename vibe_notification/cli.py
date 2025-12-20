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
from .i18n import set_language, t
from .input_utils import InputManager, select_language


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

    return parser.parse_args()


def interactive_config() -> None:
    """交互式配置"""
    # 首先选择语言
    language = select_language()
    set_language(language)

    print(f"\n{t('config_title')}")
    print(f"{t('press_esc_to_exit')}")
    print(f"{t('press_enter_to_skip')}\n")

    config = load_config()

    # 显示当前配置 - 使用整齐的格式
    print(f"\n{t('current_config')}")

    # 定义字段列表
    fields = [
        (t('sound_notification'), t('enable') if config.enable_sound else t('disable')),
        (t('system_notification'), t('enable') if config.enable_notification else t('disable')),
        (t('log_level'), config.log_level),
        (t('notification_timeout'), f"{config.notification_timeout} ms"),
        (t('sound_type'), config.sound_type),
        (t('sound_volume'), f"{config.sound_volume:.1f}")
    ]

    # 计算最大字段长度
    max_len = max(len(field[0]) for field in fields)

    # 打印对齐的配置项
    for field_name, field_value in fields:
        padding = max_len - len(field_name) + 2
        print(f"  [{field_name}]{' ' * padding}: {field_value}")

    with InputManager() as im:
        # 询问是否修改配置
        print(f"\n{t('modify_config')} ", end='')
        answer = im.ask_yes_no("", default=True)
        if answer is None:  # 用户按 Esc
            print(f"\n{t('config_cancelled')}")
            return
        if not answer:
            return

        print("\n--- " + t('modify_config') + " ---")

        # 声音通知开关
        current_status = t('enable') if config.enable_sound else t('disable')
        prompt = f"\n{t('sound_notification')} (y/n) [{current_status}]: "
        answer = im.ask_yes_no(prompt, default=config.enable_sound)
        if answer is None:  # 用户按 Esc
            print(f"\n{t('config_cancelled')}")
            return
        if answer is not None:
            config.enable_sound = answer

        # 系统通知开关
        current_status = t('enable') if config.enable_notification else t('disable')
        prompt = f"{t('system_notification')} (y/n) [{current_status}]: "
        answer = im.ask_yes_no(prompt, default=config.enable_notification)
        if answer is None:  # 用户按 Esc
            print(f"\n{t('config_cancelled')}")
            return
        if answer is not None:
            config.enable_notification = answer

        # 日志级别
        prompt = f"\n{t('log_level')} (DEBUG/INFO/WARNING/ERROR) [{config.log_level}]: "
        answer = im.ask_input(
            prompt,
            default=config.log_level,
            validator=lambda x: x in ["DEBUG", "INFO", "WARNING", "ERROR"]
        )
        if answer is None:  # 用户按 Esc
            print(f"\n{t('config_cancelled')}")
            return
        if answer is not None:
            config.log_level = answer

        # 通知超时时间
        prompt = f"\n{t('notification_timeout')} (ms) [{config.notification_timeout}]: "
        answer = im.ask_input(
            prompt,
            default=str(config.notification_timeout),
            validator=lambda x: x.isdigit() and int(x) > 0
        )
        if answer is None:  # 用户按 Esc
            print(f"\n{t('config_cancelled')}")
            return
        if answer is not None:
            config.notification_timeout = int(answer)

        # 声音类型
        valid_sounds = ["Glass", "Ping", "Pop", "Tink", "Basso"]
        prompt = f"\n{t('sound_type')} (Glass/Ping/Pop/Tink/Basso) [{config.sound_type}]: "
        answer = im.ask_input(
            prompt,
            default=config.sound_type,
            validator=lambda x: x in valid_sounds
        )
        if answer is None:  # 用户按 Esc
            print(f"\n{t('config_cancelled')}")
            return
        if answer is not None:
            config.sound_type = answer

        # 声音大小
        volume_str = f"{config.sound_volume:.1f}"
        prompt = f"\n{t('sound_volume')} (0.0-1.0) [{volume_str}]: "
        answer = im.ask_input(
            prompt,
            default=volume_str,
            validator=lambda x: (
                x.replace('.', '', 1).isdigit() and
                0.0 <= float(x) <= 1.0
            )
        )
        if answer is None:  # 用户按 Esc
            print(f"\n{t('config_cancelled')}")
            return
        if answer is not None:
            config.sound_volume = float(answer)

    # 保存配置
    save_config(config)
    print(f"\n{t('config_saved')}")


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
