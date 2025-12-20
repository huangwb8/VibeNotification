"""
测试平台适配器模块
"""

import pytest
from unittest.mock import Mock, patch
from vibe_notification.adapters import (
    DefaultCommandExecutor,
    MacOSAdapter,
    LinuxAdapter,
    WindowsAdapter,
    ProcessResult,
    create_platform_adapter,
    UnsupportedPlatformError
)
from tests.conftest import command_result_success, command_result_failure


class TestProcessResult:
    """测试命令执行结果"""

    def test_success(self):
        """测试成功结果"""
        result = ProcessResult(0, "output", "error")
        assert result.success is True
        assert result.return_code == 0
        assert result.stdout == "output"
        assert result.stderr == "error"

    def test_failure(self):
        """测试失败结果"""
        result = ProcessResult(1, "output", "error")
        assert result.success is False
        assert result.return_code == 1


class TestDefaultCommandExecutor:
    """测试默认命令执行器"""

    def test_execute_success(self):
        """测试成功执行命令"""
        executor = DefaultCommandExecutor()

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="success",
                stderr=""
            )

            result = executor.execute(["echo", "test"])

            assert result.success is True
            assert result.stdout == "success"
            mock_run.assert_called_once_with(
                ["echo", "test"],
                shell=False,
                capture_output=True,
                text=True,
                check=False
            )

    def test_execute_failure(self):
        """测试执行命令失败"""
        executor = DefaultCommandExecutor()

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="error"
            )

            result = executor.execute(["false"])

            assert result.success is False
            assert result.return_code == 1

    def test_execute_with_timeout_success(self):
        """测试带超时的成功执行"""
        executor = DefaultCommandExecutor()

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="success",
                stderr=""
            )

            result = executor.execute_with_timeout(["echo", "test"], 5.0)

            assert result.success is True
            mock_run.assert_called_once_with(
                ["echo", "test"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5.0
            )

    def test_execute_shell(self):
        """测试 shell 执行"""
        executor = DefaultCommandExecutor()

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="success",
                stderr=""
            )

            executor.execute("echo test", shell=True)

            mock_run.assert_called_once_with(
                "echo test",
                shell=True,
                capture_output=True,
                text=True,
                check=False
            )


class TestMacOSAdapter:
    """测试 macOS 适配器"""

    def test_play_sound_default(self, mock_executor):
        """测试播放默认声音"""
        adapter = MacOSAdapter(mock_executor)

        adapter.play_sound(sound_type="default")

        # 验证调用参数
        mock_executor.execute.assert_called_once()
        args = mock_executor.execute.call_args[0][0]
        assert "afplay" in args
        assert any("Glass" in arg for arg in args)

    def test_play_sound_success(self, mock_executor):
        """测试播放成功声音"""
        adapter = MacOSAdapter(mock_executor)

        adapter.play_sound(sound_type="success")

        args = mock_executor.execute.call_args[0][0]
        assert any("Glass" in arg for arg in args)

    def test_play_sound_file(self, mock_executor):
        """测试播放声音文件"""
        adapter = MacOSAdapter(mock_executor)
        sound_file = "/path/to/sound.wav"

        adapter.play_sound(sound_file=sound_file)

        mock_executor.execute.assert_called_once_with(["afplay", sound_file])

    def test_show_notification(self, mock_executor):
        """测试显示通知"""
        adapter = MacOSAdapter(mock_executor)

        adapter.show_notification("Title", "Message")

        mock_executor.execute.assert_called_once()
        command = mock_executor.execute.call_args[0][0]
        assert command[0] == "osascript"
        assert "-e" in command

    def test_show_notification_with_subtitle(self, mock_executor):
        """测试显示带副标题的通知"""
        adapter = MacOSAdapter(mock_executor)

        adapter.show_notification("Title", "Message", "Subtitle")

        mock_executor.execute.assert_called_once()
        command = mock_executor.execute.call_args[0][0]
        assert "Subtitle" in " ".join(command)

    @patch('vibe_notification.utils.check_command')
    def test_is_sound_available(self, mock_check_command):
        """测试检查声音功能可用性"""
        mock_check_command.return_value = True
        adapter = MacOSAdapter(Mock())

        assert adapter.is_sound_available() is True
        mock_check_command.assert_called_with("afplay")

    @patch('vibe_notification.utils.check_command')
    def test_is_notification_available(self, mock_check_command):
        """测试检查通知功能可用性"""
        mock_check_command.return_value = True
        adapter = MacOSAdapter(Mock())

        assert adapter.is_notification_available() is True
        mock_check_command.assert_called_with("osascript")


class TestLinuxAdapter:
    """测试 Linux 适配器"""

    def test_play_sound_default(self, mock_executor):
        """测试播放默认声音"""
        adapter = LinuxAdapter(mock_executor)

        adapter.play_sound()

        # 验证调用了 paplay 或 aplay
        mock_executor.execute.assert_called_once()
        args = mock_executor.execute.call_args[0][0]
        assert args[0] in ["paplay", "aplay"]

    def test_play_sound_file(self, mock_executor):
        """测试播放声音文件"""
        adapter = LinuxAdapter(mock_executor)
        sound_file = "/path/to/sound.wav"

        with patch('pathlib.Path.exists', return_value=True):
            adapter.play_sound(sound_file=sound_file)

        mock_executor.execute.assert_called()
        args = mock_executor.execute.call_args[0][0]
        assert sound_file in " ".join(args)

    def test_show_notification(self, mock_executor):
        """测试显示通知"""
        adapter = LinuxAdapter(mock_executor)

        adapter.show_notification("Title", "Message")

        mock_executor.execute.assert_called_once()
        args = mock_executor.execute.call_args[0][0]
        assert "notify-send" in args
        assert "Title" in args
        assert "Message" in args

    @patch('vibe_notification.utils.check_command')
    def test_is_sound_available_paplay(self, mock_check_command):
        """测试检查声音功能可用性 - paplay"""
        mock_check_command.side_effect = lambda cmd: cmd == "paplay"
        adapter = LinuxAdapter(Mock())

        assert adapter.is_sound_available() is True

    @patch('vibe_notification.utils.check_command')
    def test_is_sound_available_aplay(self, mock_check_command):
        """测试检查声音功能可用性 - aplay"""
        mock_check_command.side_effect = lambda cmd: cmd == "aplay"
        adapter = LinuxAdapter(Mock())

        assert adapter.is_sound_available() is True

    @patch('vibe_notification.utils.check_command')
    def test_is_sound_available_none(self, mock_check_command):
        """测试检查声音功能可用性 - 无"""
        mock_check_command.return_value = False
        adapter = LinuxAdapter(Mock())

        assert adapter.is_sound_available() is False


class TestWindowsAdapter:
    """测试 Windows 适配器"""

    def test_play_sound_default(self, mock_executor):
        """测试播放默认声音"""
        adapter = WindowsAdapter(mock_executor)

        adapter.play_sound()

        mock_executor.execute.assert_called_once()
        command = mock_executor.execute.call_args[0][0]
        assert "powershell.exe" in command

    def test_play_sound_file(self, mock_executor):
        """测试播放声音文件"""
        adapter = WindowsAdapter(mock_executor)
        sound_file = "C:\\path\\to\\sound.wav"

        with patch('pathlib.Path.exists', return_value=True):
            adapter.play_sound(sound_file=sound_file)

        command = mock_executor.execute.call_args[0][1]
        assert sound_file in command

    def test_show_notification(self, mock_executor):
        """测试显示通知"""
        adapter = WindowsAdapter(mock_executor)

        adapter.show_notification("Title", "Message")

        mock_executor.execute.assert_called_once()
        command = mock_executor.execute.call_args[0][0]
        assert "powershell.exe" in command
        assert "Title" in " ".join(command)
        assert "Message" in " ".join(command)

    @patch('vibe_notification.utils.check_command')
    def test_is_sound_available(self, mock_check_command):
        """测试检查声音功能可用性"""
        mock_check_command.return_value = True
        adapter = WindowsAdapter(Mock())

        assert adapter.is_sound_available() is True
        mock_check_command.assert_called_with("powershell.exe")


@patch('vibe_notification.utils.get_platform_info')
@patch('vibe_notification.adapters.DefaultCommandExecutor')
def test_create_platform_adapter(mock_executor_class, mock_get_platform_info):
    """测试创建平台适配器"""
    mock_get_platform_info.return_value = {"system": "Darwin"}
    mock_executor = Mock()
    mock_executor_class.return_value = mock_executor

    adapter = create_platform_adapter()

    assert isinstance(adapter, MacOSAdapter)
    mock_executor_class.assert_called_once()