#!/usr/bin/env python3
"""
高级输入工具模块

支持 Esc 键退出和 Enter 键跳过功能
"""

import sys
import tty
import termios
from typing import Optional, Callable, Any
from .i18n import t

class InputManager:
    """高级输入管理器"""

    def __init__(self):
        self.old_settings = None
        self.should_exit = False
        self.raw_mode = False

    def __enter__(self):
        """进入上下文管理器，设置终端为原始模式"""
        if sys.stdin.isatty():
            self.old_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())
            # 保留换行转换，避免输出时出现“阶梯式”换行
            new_settings = termios.tcgetattr(sys.stdin)
            new_settings[1] |= termios.OPOST | termios.ONLCR
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, new_settings)
            self.raw_mode = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器，恢复终端设置"""
        if self.old_settings and sys.stdin.isatty():
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
            self.raw_mode = False

    def get_char(self) -> str:
        """获取单个字符输入"""
        if sys.stdin.isatty():
            try:
                ch = sys.stdin.read(1)
                return ch
            except:
                return ''
        else:
            # 非终端环境，使用普通输入
            return input()

    def detect_escape(self, timeout: float = 0.1) -> bool:
        """检测是否按下 Esc 键"""
        if not sys.stdin.isatty():
            return False

        import select
        # 检查是否有输入等待
        if select.select([sys.stdin], [], [], timeout) == ([sys.stdin], [], []):
            ch = sys.stdin.read(1)
            # Esc 键的 ASCII 码是 27，但可能会有其他字符
            if ord(ch) == 27:
                # 读取可能的后续字符（ESC 序列）
                if select.select([sys.stdin], [], [], timeout) == ([sys.stdin], [], []):
                    # 有后续字符，说明可能是方向键等功能键
                    sys.stdin.read(2)  # 丢弃剩余字符
                    return False
                else:
                    # 纯 Esc 键
                    return True
            else:
                # 其他键，放回输入缓冲区（如果可能）
                # 这里简化处理，直接返回 False
                return False
        return False

    def ask_yes_no(self, prompt: str, default: Optional[bool] = None) -> Optional[bool]:
        """
        询问是/否问题
        返回: True/False 或 None（用户按 Esc）
        """
        if prompt:
            print(prompt, end='', flush=True)

        with self:
            while True:
                # 检查 Esc 键
                if self.detect_escape():
                    print()
                    return None

                # 获取输入
                if sys.stdin.isatty():
                    ch = self.get_char().lower()
                    if ch == '\x1b':  # Esc 直接退出
                        print()
                        return None
                    if ch == '\r' or ch == '\n':
                        print()
                        return default
                    elif ch in ['y', 'n']:
                        print(ch)
                        return ch == 'y'
                    else:
                        # 无效输入，显示提示并继续
                        print(t('invalid_input'))
                        print(prompt, end='', flush=True)
                else:
                    # 非终端环境，使用普通输入
                    try:
                        answer = input().strip().lower()
                        if not answer:
                            print()
                            return default
                        elif answer in ['y', 'n']:
                            print(answer)
                            return answer == 'y'
                        else:
                            print(t('invalid_input'))
                            print(prompt, end='', flush=True)
                    except (EOFError, KeyboardInterrupt):
                        print()
                        return None

    def ask_input(self, prompt: str, default: Optional[str] = None,
                  validator: Optional[Callable[[str], bool]] = None) -> Optional[str]:
        """
        询问输入
        返回: 输入的字符串 或 None（用户按 Esc）
        """
        if prompt:
            print(prompt, end='', flush=True)

        with self:
            while True:
                # 检查 Esc 键
                if self.detect_escape():
                    print()
                    return None

                # 获取整行输入
                if sys.stdin.isatty():
                    # 使用 line_input 函数获取整行
                    line = self._line_input()
                    if line == '\x1b':  # Esc
                        print()
                        return None

                    if not line.strip():
                        print()
                        return default

                    # 验证输入
                    if validator:
                        if validator(line.strip()):
                            print()
                            return line.strip()
                        else:
                            print(t('invalid_input'))
                            print(prompt, end='', flush=True)
                    else:
                        print()
                        return line.strip()
                else:
                    # 非终端环境
                    try:
                        line = input()
                        if not line.strip():
                            print()
                            return default

                        if validator:
                            if validator(line.strip()):
                                print(line.strip())
                                return line.strip()
                            else:
                                print(t('invalid_input'))
                                print(prompt, end='', flush=True)
                        else:
                            print(line.strip())
                            return line.strip()
                    except (EOFError, KeyboardInterrupt):
                        print()
                        return None

    def _line_input(self) -> str:
        """读取一行输入（在原始模式下）"""
        chars = []
        while True:
            ch = self.get_char()
            if ch == '\r' or ch == '\n':
                print()  # 换行
                return ''.join(chars)
            elif ch == '\x7f' or ch == '\b':  # Backspace
                if chars:
                    chars.pop()
                    print('\b \b', end='', flush=True)
            elif ch == '\x1b':  # Esc
                return ch
            else:
                chars.append(ch)
                print(ch, end='', flush=True)


def select_language() -> str:
    """选择语言"""
    print("\n" + "="*30)
    print(t('select_language'))
    print("1. " + t('chinese'))
    print("2. " + t('english'))
    print("="*30)

    with InputManager() as im:
        while True:
            print("选择 (1-2): ", end='', flush=True)

            # 检查 Esc 键（这里使用默认中文）
            if im.detect_escape():
                return "zh"  # 默认中文

            if sys.stdin.isatty():
                ch = im.get_char()
                if ch == '1':
                    print("1")
                    return "zh"
                elif ch == '2':
                    print("2")
                    return "en"
                elif ch in ['\r', '\n']:
                    print()
                    return "zh"  # 默认中文
                else:
                    print(f"\n{t('invalid_input')} (1-2)")
            else:
                try:
                    answer = input().strip()
                    if answer == '1':
                        return "zh"
                    elif answer == '2':
                        return "en"
                    elif not answer:
                        return "zh"  # 默认中文
                    else:
                        print(f"\n{t('invalid_input')} (1-2)")
                except (EOFError, KeyboardInterrupt):
                    # 非交互式环境或用户中断，返回默认语言
                    return "zh"
