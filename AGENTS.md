# 仓库指南（Agent 速览）

## 快速开始（本地开发）
1. `python -m venv venv`；`source venv/bin/activate`
2. `pip install -e .`
3. `python -m vibe_notification --test` 验证通知链路
4. `python -m pytest tests/` 运行回归

## 目录速查
- `vibe_notification/`：核心包，含 CLI、配置、模型、通知器、解析器、检测器
- `tests/`：pytest 用例（如 `test_notification.py`）
- `docs/`：扩展文档；`examples/`：示例集成
- 根脚本（如 `notify.py`）为兼容入口；`config.example.json` 提供配置示例

## 代码与风格
- Python 4 空格缩进，遵循 PEP 8：模块 `snake_case`，类 `CapWords`，常量 `UPPER_CASE`
- 推荐本地启用 `black`、`isort`、`flake8`、`mypy`（使用默认配置）
- 公共 API 入口：`vibe_notification/__init__.py`；CLI 入口：`vibe_notification/cli.py`

## 测试要求
- 测试文件命名 `test_*.py`，统一放在 `tests/`
- 新功能需配测试；修复须补回归用例
- 涉及平台差异的逻辑，至少提供模拟或条件分支测试

## 提交与 PR
- 优先遵循 CONTRIBUTING 中的 Conventional Commits（如 `feat:`、`fix:`、`docs:`）
- PR 需包含：变更描述、测试结果、必要的文档/配置更新，并关联相关 issue

## 配置与安全
- 请复制 `config.example.json` 为 `config.json` 使用，避免提交本地路径或敏感信息
- 日志输出在 `vibe_notification.log`，对外分享前请检查内容

## Agent 对话约定
- 与本仓库相关的对话请使用中文收尾，语气保持专业、简洁
