#!/usr/bin/env python3
"""
命令行入口模块

提供命令行接口
"""

import sys
import argparse
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence, Tuple
from .core import VibeNotifier
from .models import NotificationConfig
from .config import load_config, save_config, get_env_config
from .doctor import format_doctor_report, run_doctor
from .i18n import set_language, t
from .input_utils import InputManager, select_language


def parse_args(argv: Optional[Sequence[str]] = None) -> Tuple[argparse.Namespace, List[str]]:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="VibeNotification - 智能 AI 助手会话结束通知系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 作为 Claude Code 钩子使用
  echo '{"toolName": "Task"}' | python -m vibe_notification

  # 作为 Codex 钩子使用
  python -m vibe_notification '{"type":"agent-turn-complete","thread-id":"thread-1","turn-id":"turn-1","cwd":"/tmp/project","input-messages":["fix tests"],"last-assistant-message":"Done"}'

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
        "--doctor",
        action="store_true",
        help="检查 Claude Code / Codex / VibeNotification 的本地集成状态"
    )

    parser.add_argument(
        "--wrap-codex",
        action="store_true",
        help="启动 Codex，并在 Codex 进程退出后只发送一次通知"
    )

    args, extra_args = parser.parse_known_args(argv)

    # wrapper 模式下，argparse 可能把第一个普通参数误吞成 event_json；
    # 对 Codex 透传参数时需要把它拼回 extra_args。
    if args.wrap_codex and args.event_json is not None:
        extra_args = [args.event_json, *extra_args]
        args.event_json = None

    return args, extra_args


def get_terminal_width() -> int:
    """获取终端宽度"""
    try:
        import shutil
        return shutil.get_terminal_size().columns
    except:
        return 80  # 默认宽度


def format_config_item(label: str, value: str, max_label_len: int, term_width: int) -> str:
    """格式化配置项，确保在终端内正确显示"""
    # 如果标签太长，缩写标签
    if len(label) > max_label_len:
        label = label[:max_label_len-1] + "·"

    # 计算可用空间
    available_space = term_width - len(label) - len(value) - 10  # 留出边距和冒号空间

    if available_space < 5:
        # 空间不足，换行显示
        return f"  [{label}]:\n    {value}"
    else:
        # 单行显示
        return f"  [{label}]: {value}"


def interactive_config() -> None:
    """交互式配置"""
    # 首先选择语言
    language = select_language()
    config = load_config()
    previous_language = getattr(config, "language", "zh")
    config.language = language
    set_language(config.language)
    language_changed = config.language != previous_language

    print(f"\n{t('config_title')}")
    print(f"{t('press_esc_to_exit')}")
    print(f"{t('press_enter_to_skip')}\n")

    term_width = get_terminal_width()

    # 显示当前配置 - 使用适应终端宽度的格式
    print(f"\n{t('current_config')}")

    # 定义字段列表，使用更短的标签
    fields = [
        (t('sound_notification'), t('enable') if config.enable_sound else t('disable')),
        (t('system_notification'), t('enable') if config.enable_notification else t('disable')),
        (t('log_level'), config.log_level),
        (t('notification_timeout'), f"{config.notification_timeout}ms"),
        (t('sound_type'), config.sound_type),
        (t('sound_volume'), f"{config.sound_volume:.1f}")
    ]

    # 计算最大字段长度，但限制在合理范围内
    max_label_len = min(max(len(field[0]) for field in fields), 12)

    # 打印格式化的配置项
    for field_name, field_value in fields:
        formatted_line = format_config_item(field_name, field_value, max_label_len, term_width)
        print(formatted_line)

    im = InputManager()

    # 询问是否修改配置
    print(f"\n{t('modify_config')} ", end='')
    answer = im.ask_yes_no("", default=True)
    if answer is None:  # 用户按 Esc
        print(f"\n{t('config_cancelled')}")
        return
    if not answer:
        if language_changed:
            save_config(config)
            print(f"\n{t('config_saved')}")
        return

    print(f"\n{t('current_config')}:")

    # 声音通知开关
    print(f"  {t('sound_hint')}")
    current_status = t('enable') if config.enable_sound else t('disable')
    prompt = f"  {t('sound_notification')} (y/n) [{current_status}]: "
    answer = im.ask_yes_no(prompt, default=config.enable_sound)
    if answer is None:  # 用户按 Esc
        print(f"\n{t('config_cancelled')}")
        return
    if answer is not None:
        config.enable_sound = answer

    # 系统通知开关
    print(f"  {t('system_hint')}")
    current_status = t('enable') if config.enable_notification else t('disable')
    prompt = f"  {t('system_notification')} (y/n) [{current_status}]: "
    answer = im.ask_yes_no(prompt, default=config.enable_notification)
    if answer is None:  # 用户按 Esc
        print(f"\n{t('config_cancelled')}")
        return
    if answer is not None:
        config.enable_notification = answer

    # 日志级别
    print(f"  {t('log_level_hint')}")
    prompt = f"  {t('log_level')} [{config.log_level}]: "
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
    print(f"  {t('timeout_hint')}")
    prompt = f"  {t('notification_timeout')} [{config.notification_timeout}]: "
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
    print(f"  {t('sound_type_hint')}")
    valid_sounds = ["Glass", "Ping", "Pop", "Tink", "Basso"]
    prompt = f"  {t('sound_type')} [{config.sound_type}]: "
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
    print(f"  {t('sound_volume_hint')}")
    volume_str = f"{config.sound_volume:.1f}"
    prompt = f"  {t('sound_volume')} [{volume_str}]: "
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


def _infer_codex_cwd(codex_args: Sequence[str]) -> str:
    """从透传给 Codex 的参数中推断工作目录。"""
    for index, value in enumerate(codex_args):
        if value in {"-C", "--cd"} and index + 1 < len(codex_args):
            return codex_args[index + 1]
    return str(Path.cwd())


def run_codex_wrapper(config: NotificationConfig, codex_args: Sequence[str]) -> int:
    """启动 Codex，并在进程退出后发送一次 session-end 通知。"""
    codex_path = shutil.which("codex")
    if not codex_path:
        print("未找到 codex 可执行文件，请先确认 Codex CLI 已安装到 PATH。", file=sys.stderr)
        return 127

    completed = subprocess.run([codex_path, *codex_args], check=False)

    notifier = VibeNotifier(config)
    from .models import NotificationEvent

    event = NotificationEvent(
        type="session-end",
        agent="codex",
        message="Codex 会话已结束",
        summary="Codex 会话已结束",
        timestamp=datetime.now().isoformat(),
        conversation_end=True,
        is_last_turn=True,
        metadata={
            "cwd": _infer_codex_cwd(codex_args),
            "exit_code": completed.returncode,
            "wrapped": True,
            "wrapped_args": list(codex_args),
        },
    )
    notifier.process_event(event)
    return completed.returncode


def main() -> None:
    """主函数"""
    args, extra_args = parse_args()

    # 显示版本
    if args.version:
        from . import __version__
        print(f"VibeNotification v{__version__}")
        return

    # 配置模式
    if args.config:
        interactive_config()
        return

    if args.doctor:
        print(format_doctor_report(run_doctor()))
        return

    # 加载配置并应用命令行参数
    config = get_env_config()
    set_language(getattr(config, "language", "zh"))
    config = update_config_from_args(config, args)

    if args.wrap_codex:
        raise SystemExit(run_codex_wrapper(config, extra_args))

    # 创建通知器
    notifier = VibeNotifier(config)

    # 测试模式
    if args.test:
        from .models import NotificationEvent
        event = NotificationEvent(
            type="test",
            agent="vibe-notification",
            message=t("test_message"),
            summary=t("test_summary"),
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
