# 仓库指南

## 项目结构与模块组织
- `vibe_notification/` 为核心包，包含 CLI、配置、模型、通知器、解析器与检测器。
- `tests/` 放置 pytest 用例（如 `test_notification.py`）。
- `docs/` 存放扩展文档，`examples/` 为示例集成。
- 根目录脚本（如 `notify.py`）是兼容入口；`config.example.json` 是配置示例。

## 构建、测试与开发命令
- `python -m venv venv` / `source venv/bin/activate`：创建并激活虚拟环境。
- `pip install -e .`：可编辑安装，便于本地开发。
- `python -m vibe_notification --test`：发送测试通知，快速验证环境。
- `python -m pytest tests/`：运行全部测试。

## 编码风格与命名约定
- Python 使用 4 空格缩进，遵循 PEP 8：模块 `snake_case`，类 `CapWords`，常量 `UPPER_CASE`。
- 文档建议使用 `black`、`isort`、`flake8`、`mypy`；如需启用，请在本地安装并保持默认配置。
- 公共 API 放在 `vibe_notification/__init__.py`，CLI 入口在 `vibe_notification/cli.py`。

## 测试规范
- 测试文件命名 `test_*.py`，统一放在 `tests/`。
- 新功能必须添加测试；修复问题需补充回归用例。
- 涉及平台差异的逻辑，至少加入模拟或条件分支测试。

## 提交与 PR 规范
- 现有历史记录较少且格式自由；请优先遵循 CONTRIBUTING 中的 Conventional Commits（如 `feat:`、`fix:`、`docs:`）。
- PR 需包含清晰描述、测试结果与必要的文档/配置更新，并关联相关 issue。

## 安全与配置提示
- 复制 `config.example.json` 为 `config.json`，避免提交本地路径或敏感信息。
- 日志输出在 `vibe_notification.log`，对外分享前请检查内容。

## Agent 使用说明
- 本仓库要求对话结束时使用中文回复；保持语气专业、简洁。
