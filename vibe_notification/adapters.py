"""
平台适配层

提供跨平台的统一接口
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path
import subprocess
import logging
from .exceptions import CommandExecutionError, UnsupportedPlatformError
from .utils import get_platform_info, check_command


class ProcessResult:
    """命令执行结果"""
    def __init__(self, return_code: int, stdout: str, stderr: str = ""):
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
        self.success = return_code == 0


class CommandExecutor(ABC):
    """命令执行器抽象基类"""

    @abstractmethod
    def execute(self, command: List[str], shell: bool = False) -> ProcessResult:
        """执行命令并返回结果"""
        pass

    @abstractmethod
    def execute_with_timeout(self, command: List[str], timeout: float) -> ProcessResult:
        """执行命令并设置超时"""
        pass


class DefaultCommandExecutor(CommandExecutor):
    """默认命令执行器实现"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def execute(self, command: List[str], shell: bool = False) -> ProcessResult:
        """执行命令"""
        try:
            self.logger.debug(f"Executing command: {' '.join(command)}")
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                check=False
            )
            return ProcessResult(
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr
            )
        except Exception as e:
            raise CommandExecutionError(command, -1, str(e))

    def execute_with_timeout(self, command: List[str], timeout: float) -> ProcessResult:
        """执行命令并设置超时"""
        try:
            self.logger.debug(f"Executing command with timeout {timeout}s: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout
            )
            return ProcessResult(
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr
            )
        except subprocess.TimeoutExpired as e:
            raise CommandExecutionError(command, -1, f"Timeout after {timeout}s")
        except Exception as e:
            raise CommandExecutionError(command, -1, str(e))


class PlatformAdapter(ABC):
    """平台适配器抽象基类"""

    @abstractmethod
    def play_sound(self, sound_file: Optional[str] = None, sound_type: str = "default", volume: float = 1.0) -> None:
        """播放声音"""
        pass

    @abstractmethod
    def show_notification(self, title: str, message: str, subtitle: str = "") -> None:
        """显示系统通知"""
        pass

    @abstractmethod
    def is_sound_available(self) -> bool:
        """检查声音功能是否可用"""
        pass

    @abstractmethod
    def is_notification_available(self) -> bool:
        """检查通知功能是否可用"""
        pass


class MacOSAdapter(PlatformAdapter):
    """macOS 平台适配器"""

    def __init__(self, executor: CommandExecutor):
        self.executor = executor
        self.logger = logging.getLogger(__name__)

    def play_sound(self, sound_file: Optional[str] = None, sound_type: str = "default", volume: float = 1.0) -> None:
        """使用 afplay 播放声音"""
        # 确保 volume 在 0.0-1.0 范围内
        volume = max(0.0, min(1.0, volume))

        if sound_file and Path(sound_file).exists():
            command = ["afplay", "--volume", str(int(volume * 100)), sound_file]
        else:
            # 使用内置系统声音
            sound_map = {
                "default": "Ping",
                "success": "Glass",
                "error": "Basso",
                "warning": "Tink",
                "ping": "Ping",
                "pop": "Pop",
                "Glass": "Glass"
            }
            sound_name = sound_map.get(sound_type, "Ping")
            command = ["afplay", "--volume", str(int(volume * 100)), "/System/Library/Sounds/" + sound_name + ".aiff"]

        result = self.executor.execute(command)
        if not result.success:
            self.logger.warning(f"Failed to play sound: {result.stderr}")

    def show_notification(self, title: str, message: str, subtitle: str = "") -> None:
        """使用 osascript 显示通知"""
        applescript = f'''
        display notification "{message}" with title "{title}"
        '''
        if subtitle:
            applescript = applescript.replace(f'title "{title}"', f'title "{title}" subtitle "{subtitle}"')

        command = ["osascript", "-e", applescript]
        result = self.executor.execute(command)
        if not result.success:
            self.logger.warning(f"Failed to show notification: {result.stderr}")

    def is_sound_available(self) -> bool:
        """检查 afplay 是否可用"""
        return check_command("afplay")

    def is_notification_available(self) -> bool:
        """检查通知功能是否可用"""
        return check_command("osascript")


class LinuxAdapter(PlatformAdapter):
    """Linux 平台适配器"""

    def __init__(self, executor: CommandExecutor):
        self.executor = executor
        self.logger = logging.getLogger(__name__)

    def play_sound(self, sound_file: Optional[str] = None, sound_type: str = "default", volume: float = 1.0) -> None:
        """使用 aplay 或 paplay 播放声音"""
        # 确保 volume 在 0.0-1.0 范围内
        volume = max(0.0, min(1.0, volume))

        if sound_file and Path(sound_file).exists():
            # 优先使用 paplay（PulseAudio），否则使用 aplay（ALSA）
            if check_command("paplay"):
                command = ["paplay", "--volume", str(int(volume * 65536)), sound_file]
            elif check_command("aplay"):
                # aplay 不支持音量控制，需要通过 amixer
                if volume < 1.0:
                    # 设置系统音量（临时）
                    self._set_system_volume(volume)
                command = ["aplay", sound_file]
            else:
                self.logger.warning("No sound player available (paplay or aplay)")
                return
        else:
            # 使用系统默认声音
            if check_command("paplay"):
                command = ["paplay", "--volume", str(int(volume * 65536)), "/usr/share/sounds/alsa/Front_Left.wav"]
            elif check_command("aplay"):
                if volume < 1.0:
                    self._set_system_volume(volume)
                command = ["aplay", "/usr/share/sounds/alsa/Front_Left.wav"]
            else:
                self.logger.warning("No sound player available")
                return

        result = self.executor.execute(command)
        if not result.success:
            self.logger.warning(f"Failed to play sound: {result.stderr}")

    def _set_system_volume(self, volume: float) -> None:
        """设置系统音量（仅对 aplay 有效）"""
        try:
            # 获取当前音量
            get_vol_cmd = ["amixer", "get", "Master"]
            current_result = self.executor.execute(get_vol_cmd)

            if current_result.success:
                # 计算新音量值（百分比）
                volume_percent = int(volume * 100)
                set_vol_cmd = ["amixer", "set", "Master", f"{volume_percent}%"]
                self.executor.execute(set_vol_cmd)
        except Exception as e:
            self.logger.warning(f"Failed to set system volume: {e}")

    def show_notification(self, title: str, message: str, subtitle: str = "") -> None:
        """使用 notify-send 显示通知"""
        command = ["notify-send", title, message]
        if subtitle:
            command.extend(["-h", f"string:x-canonical-private-synchronous: {subtitle}"])

        result = self.executor.execute(command)
        if not result.success:
            self.logger.warning(f"Failed to show notification: {result.stderr}")

    def is_sound_available(self) -> bool:
        """检查声音播放器是否可用"""
        return check_command("paplay") or check_command("aplay")

    def is_notification_available(self) -> bool:
        """检查 notify-send 是否可用"""
        return check_command("notify-send")


class WindowsAdapter(PlatformAdapter):
    """Windows 平台适配器"""

    def __init__(self, executor: CommandExecutor):
        self.executor = executor
        self.logger = logging.getLogger(__name__)

    def play_sound(self, sound_file: Optional[str] = None, sound_type: str = "default", volume: float = 1.0) -> None:
        """使用 PowerShell 播放声音"""
        # 确保 volume 在 0.0-1.0 范围内
        volume = max(0.0, min(1.0, volume))

        if sound_file and Path(sound_file).exists():
            # 对于自定义音频文件，设置音量并播放
            ps_command = f'''
            $player = New-Object Media.SoundPlayer "{sound_file}";
            $player.PlaySync();
            '''
        else:
            # 使用系统默认声音
            sound_map = {
                "default": "Asterisk",
                "success": "Asterisk",
                "error": "Exclamation",
                "warning": "Exclamation",
                "Glass": "Asterisk"
            }
            sound_name = sound_map.get(sound_type, "Asterisk")
            ps_command = f'[system.media.systemsounds]::{sound_name}.Play();'

        # 添加音量控制（通过设置系统音量）
        if volume < 1.0:
            volume_cmd = f'''
            [audio]::Volume = {volume};
            '''
            ps_command = volume_cmd + ps_command

        command = ["powershell.exe", "-Command", ps_command]
        result = self.executor.execute(command)
        if not result.success:
            self.logger.warning(f"Failed to play sound: {result.stderr}")

    def show_notification(self, title: str, message: str, subtitle: str = "") -> None:
        """使用 Windows Toast 通知"""
        full_title = f"{title} - {subtitle}" if subtitle else title

        # 先尝试使用Toast通知（Windows 10/11）
        ps_command_toast = f'''
        try {{
            Add-Type -AssemblyName System.Runtime.WindowsRuntime
            $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where {{ $_.Name -eq 'AsTask' }} | Where {{$_.GetParameters().Count -eq 1}})[0]
            Function Await($WinRtTask, $ResultSig) {{
                $asTask = $asTaskGeneric.MakeGenericMethod($ResultSig)
                $netTask = $asTask.Invoke($null, @($WinRtTask))
                $netTask.Wait(-1) | Out-Null
            }}
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null
            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml("<toast><visual><binding template='ToastGeneric'><text>{full_title}</text><text>{message}</text></binding></visual></toast>")
            $toast = New-Object Windows.UI.Notifications.ToastNotification($xml)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("VibeNotification").Show($toast)
        }} catch {{
            exit 1
        }}
        '''

        # 尝试执行Toast通知
        self.logger.debug(f"Attempting to send Toast notification: {full_title}")
        command = ["powershell.exe", "-Command", ps_command_toast]
        result = self.executor.execute(command)

        if result.stdout:
            self.logger.debug(f"Toast stdout: {result.stdout.strip()}")
        if result.stderr:
            self.logger.debug(f"Toast stderr: {result.stderr.strip()}")

        # 如果Toast失败，回退到NotifyIcon
        if not result.success:
            self.logger.warning("Toast notification failed, falling back to NotifyIcon")
            ps_command = f'''
            Add-Type -AssemblyName System.Windows.Forms;
            Add-Type -AssemblyName System.Drawing;
            $notification = New-Object System.Windows.Forms.NotifyIcon;
            $notification.Icon = [System.Drawing.SystemIcons]::Information;
            $notification.BalloonTipTitle = "{full_title}";
            $notification.BalloonTipText = "{message}";
            $notification.Visible = $true;
            $notification.ShowBalloonTip(10000);
            Write-Host "NotifyIcon notification sent"
            Start-Sleep 2;
            $notification.Dispose();
            '''

            command = ["powershell.exe", "-Command", ps_command]
            result = self.executor.execute(command)
            if result.success:
                self.logger.info("NotifyIcon fallback succeeded")
            else:
                self.logger.warning(f"Failed to show notification: {result.stderr}")
        else:
            self.logger.info("Toast notification sent successfully")

    def is_sound_available(self) -> bool:
        """检查 PowerShell 是否可用"""
        return check_command("powershell.exe")

    def is_notification_available(self) -> bool:
        """检查 PowerShell 是否可用"""
        return check_command("powershell.exe")


def create_platform_adapter(executor: CommandExecutor) -> PlatformAdapter:
    """创建平台适配器"""
    platform_info = get_platform_info()

    # 检查是否在WSL环境中
    is_wsl = False
    if platform_info["system"] == "Linux":
        try:
            with open("/proc/version", "r") as f:
                version_info = f.read().lower()
                if "microsoft" in version_info or "wsl" in version_info:
                    is_wsl = True
        except:
            pass

    if platform_info["system"] == "Darwin":
        return MacOSAdapter(executor)
    elif is_wsl or platform_info["system"] == "Windows":
        # WSL环境使用Windows适配器
        return WindowsAdapter(executor)
    elif platform_info["system"] == "Linux":
        return LinuxAdapter(executor)
    else:
        raise UnsupportedPlatformError(platform_info["system"])