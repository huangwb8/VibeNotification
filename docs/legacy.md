## 故障排除

### Claude Code 钩子不生效？

1. **检查配置文件格式**：
   ```bash
   # 验证 JSON 格式是否正确
   python -m json.tool ~/.claude/config.json
   ```

2. **确认 Python 路径**：
   ```bash
   # 查看当前使用的 Python 路径
   which python
   
   # 如果使用虚拟环境，需要完整路径
   which python  # 在激活的虚拟环境中执行
   ```

3. **手动测试钩子**：
   ```bash
   # 模拟 Claude Code 传递的数据
   echo '{"toolName": "Read"}' | python -m vibe_notification
   ```

4. **查看 Claude Code 日志**：
   ```bash
   # Claude Code 日志位置
   ~/.claude/logs/
   ```

### 通知不显示？

1. **macOS 权限设置**：
   - 系统偏好设置 → 安全性与隐私 → 通知 → 允许终端/你的终端应用发送通知

2. **安装 terminal-notifier**（推荐）：
   ```bash
   brew install terminal-notifier
   ```

3. **测试系统通知**：
   ```bash
   # 直接测试通知功能
   python -m vibe_notification --test
   ```

## 小贴士
- macOS 建议安装 `terminal-notifier` 以确保弹窗稳定：`brew install terminal-notifier`（未安装会回退 AppleScript，部分环境可能被系统权限阻挡）
- 日志会写入仓库根目录的 `vibe_notification.log`，排查问题时可查看。
- 使用虚拟环境时，记得在配置文件中使用完整的 Python 解释器路径。