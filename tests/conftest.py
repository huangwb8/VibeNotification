"""
pytest 配置文件

提供共享的 fixtures
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from vibe_notification.models import (
    NotificationConfig,
    NotificationEvent,
    NotificationLevel,
    PlatformType
)
from vibe_notification.adapters import (
    PlatformAdapter,
    CommandExecutor,
    ProcessResult,
    DefaultCommandExecutor
)
from vibe_notification.factories import (
    ParserFactory,
    NotifierFactory,
    AdapterFactory
)


@pytest.fixture
def mock_config():
    """模拟配置对象"""
    return NotificationConfig(
        enable_sound=True,
        enable_notification=True,
        sound_type="default",
        notification_timeout=5000,
        log_level="INFO"
    )


@pytest.fixture
def sample_event():
    """示例事件对象"""
    return NotificationEvent(
        type="conversation_end",
        agent="claude-code",
        message="会话已完成",
        summary="成功完成了代码生成任务",
        timestamp=datetime.now().isoformat(),
        conversation_end=True,
        is_last_turn=True,
        tool_name="claude-code"
    )


@pytest.fixture
def mock_executor():
    """模拟命令执行器"""
    executor = Mock(spec=DefaultCommandExecutor)
    executor.execute.return_value = ProcessResult(
        return_code=0,
        stdout="Success",
        stderr=""
    )
    return executor


@pytest.fixture
def mock_platform_adapter():
    """模拟平台适配器"""
    adapter = Mock(spec=PlatformAdapter)
    adapter.is_sound_available.return_value = True
    adapter.is_notification_available.return_value = True
    return adapter


@pytest.fixture
def test_event_data():
    """测试事件数据"""
    return {
        "type": "conversation_end",
        "agent": "claude-code",
        "message": "测试消息",
        "summary": "测试摘要",
        "timestamp": "2024-01-01T12:00:00",
        "conversation_end": True,
        "is_last_turn": True,
        "tool_name": "claude-code"
    }


@pytest.fixture
def command_result_success():
    """成功的命令执行结果"""
    return ProcessResult(
        return_code=0,
        stdout="Command succeeded",
        stderr=""
    )


@pytest.fixture
def command_result_failure():
    """失败的命令执行结果"""
    return ProcessResult(
        return_code=1,
        stdout="",
        stderr="Command failed"
    )


@pytest.fixture(scope="session")
def test_configs():
    """测试配置集合"""
    return {
        "default": NotificationConfig(),
        "sound_only": NotificationConfig(
            enable_sound=True,
            enable_notification=False
        ),
        "notification_only": NotificationConfig(
            enable_sound=False,
            enable_notification=True
        ),
        "all_disabled": NotificationConfig(
            enable_sound=False,
            enable_notification=False
        )
    }