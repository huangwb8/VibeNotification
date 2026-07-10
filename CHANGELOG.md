# 更新日志

所有项目的显著更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.25] - 2026-07-11

### 修复
- Claude Code Stop 去重改用稳定的 assistant `message.id`，避免同一回复的增量 transcript
  快照产生连续提示；稳定 ID 保留 24 小时，新版 `last_assistant_message` 优先于可能
  滞后的 transcript。
- 识别 Claude Code `background_tasks` 与 `session_crons`，后台工作仍会继续时不提示。
- 未知 Claude hook 在适配前强制静默，防止未来事件误落入通用终态解析。
- Codex 按 `thread-id` + `turn-id` 做跨进程原子幂等，重复 notify 只处理一次。
- Codex 输入及其它 hook 生命周期事件强制静默，即使关闭结束检测也不会误提示。
- 带稳定 turn 身份的官方 `agent-turn-complete` 直接按事件语义处理，短回复不再漏报。
- 未知或新版未识别事件改为安全跳过；测试通知仅能由显式 `--test` 触发。

### 测试
- 新增 Claude 增量消息、滞后 transcript、后台任务、未知 hook，Codex 重复 turn、
  短回复、用户输入静默，以及线程/真实多进程幂等回归测试。

## [1.0.21] - 2026-06-18

### 修复
- 修复 Claude Code 新版本下 Stop 钩子被高频触发导致通知泛滥的问题
- Claude Code 新版在 agentic loop 中（工具调用、子代理）也会触发 Stop 钩子，
  不再仅限于主代理回复结束。新增基于 `transcript_path` 真实状态的中间停止判定：
  - 最后一条 assistant 消息仍在调用工具（content 含 `tool_use`）→ 中间停止，跳过通知
  - `stop_hook_active=True` 的 Stop 链重复触发 → 跳过，避免重复通知
  - 无 `transcript_path` 或读取失败 → 保守通知，避免漏报
- 现在仅在「主代理一次完整回复真正结束」时通知一次，满足「某个回复结束就通知」的需求

### 测试
- 新增回归测试覆盖中间停止、真正回复结束、transcript 尾部元数据行跳过、
  `stop_hook_active` 去重、transcript 缺失/损坏回退等场景

## [1.0.5] - 2026-03-21

### 修复
- 修复 Codex 中间事件也会触发通知的过度报告问题
- 默认仅在 `conversation_end=True` 时发送通知，非结束事件直接跳过
- 收紧结束事件检测逻辑，不再将 `assistant-message` 直接视为一轮完成

### 测试
- 新增回归测试，覆盖“非结束事件不通知”和“`agent-turn-complete` 仍正常通知”

## [1.0.0] - 2025-12-20

### 新增
- 初始版本发布
- 核心通知引擎 `VibeNotifier` 类
- 跨平台支持：macOS、Linux、Windows
- Claude Code 钩子集成
- Codex 事件兼容性
- 智能会话结束检测
- 可配置的通知行为
- 详细日志记录
- 完整的测试套件
- 示例代码和文档

### 功能
- 自动检测 Claude Code 和 Codex 会话结束
- 原生系统通知（支持标题、内容、副标题）
- 可配置的通知声音
- 多级别通知（信息、成功、警告、错误）
- 向后兼容原 `notify.py` 脚本
- 配置文件支持
- 模块化设计，易于扩展

### 技术特性
- 基于 Python 3.7+
- 使用 dataclass 和 Enum 进行类型安全
- 完整的错误处理和回退机制
- 详细的日志记录到文件
- 单元测试覆盖核心功能
- 代码质量检查（Black、isort、flake8、mypy）

### 文档
- 详细的 README.md
- 安装和配置指南
- 快速开始示例
- 开发环境设置
- 贡献指南
- API 文档

## [0.1.0] - 2025-12-01

### 新增
- 项目初始概念
- 基础通知功能原型
- 跨平台兼容性研究

---

## 版本规则

### 版本号格式：主版本号.次版本号.修订号

- **主版本号**：不兼容的 API 修改
- **次版本号**：向下兼容的功能性新增
- **修订号**：向下兼容的问题修正

### 发布周期

- **主版本**：重大更新，可能包含不兼容的更改
- **次版本**：每月或每季度发布，包含新功能
- **修订版本**：根据需要发布，修复重要问题

## 升级指南

### 从旧版本升级

#### 升级到 1.0.0
- 完全重写，但保持 API 兼容性
- 新增配置系统
- 改进的错误处理
- 更详细的日志记录
- 建议查看 README 中的新功能

### 向后兼容性

- 版本 1.x.x 将保持 API 兼容性
- 破坏性更改将在 2.0.0 中引入
- 弃用的功能将在次版本中标记，在主版本中移除

## 未来计划

### 计划中的功能
- Webhook 集成
- 自定义通知模板
- 移动端支持
- 更多 AI 助手集成
- 高级分析功能

### 已知问题
- 查看 GitHub Issues 了解当前问题

---

## 链接

- [GitHub 仓库](https://github.com/yourusername/VibeNotification)
- [问题追踪](https://github.com/yourusername/VibeNotification/issues)
- [文档](https://github.com/yourusername/VibeNotification/docs)
