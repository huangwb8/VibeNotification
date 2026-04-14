# 基本

- 目前的版本

```
python -m vibe_notification --version
```

- 升级

```
version=1.0.11
pyproject.toml里软件版本升级为{version}。创建tag v{version}；使用 git-commit skill创建commit信息；通过git-publish-release skill 发布release。然后，在 /Volumes/2T01/softwares/anoconda/anaconda3/bin/python 这个默认的conda的python里安装这个版本。
```

- 通用开发软件的prompt

```
使用 awesome-code skill 辅助规划、优化。所有问题都要解决。 如果工作时有疑问，或者有更好的方案，自己选个最优方案优化，不要问我。不要破坏其它功能。要保证最终成品能正常、稳定、高效地工作。 

根据 docs/plans/SDK-沙箱机制-v202602231445.md， 使用 awesome-code skill 优化代码，所有问题都要解决，所有意见都要落实。 如果工作时有疑问，或者有更好的方案，自己选个最优方案优化，不要问我。 不要破坏其它功能。 要保证最终成品能正常、稳定、高效地工作。 
```

- 如果不行了，问

```
Claude Code 完成一轮回复，也不会收到通知。 是本机codex的config.toml有问题，还是vibe notification的源代码有问题？
Codex 完成一轮回复，也不会收到通知。是本机codex的config.toml有问题，还是vibe notification的源代码有问题？
```

# 日常

---

还是不行。 我希望：
- 用户在codex里输入命令
- codex开始工作
- codex结束本次回复
- 触发通知
目前没法做到这样； 我已经在codex里进行测试。 问题出在哪？

---

Claude Code 完成一轮回复，也不会收到弹窗通知。 是本机codex的config.toml有问题，还是vibe notification的源代码有问题？使用 awesome-code skill 辅助规划、优化。所有问题都要解决。 如果工作时有疑问，或者有更好的方案，自己选个最优方案优化，不要问我。不要破坏其它功能。要保证最终成品能正常、稳定、高效地工作。 

Codex 完成一轮回复，也不会收到弹窗通知。是本机codex的config.toml有问题，还是vibe notification的源代码有问题？使用 awesome-code skill 辅助规划、优化。所有问题都要解决。 如果工作时有疑问，或者有更好的方案，自己选个最优方案优化，不要问我。不要破坏其它功能。要保证最终成品能正常、稳定、高效地工作。 

---

目前，本设备里的claude code/codex的提示似乎不生效了：尽管会话结束，仍然收不到vibe notification的通知。 这是为什么？ 如果是程序有bug，请使用 awesome-code skill 辅助规划、优化。所有问题都要解决。 如果工作时有疑问，或者有更好的方案，自己选个最优方案优化，不要问我。不要破坏其它功能。要保证最终成品能正常、稳定、高效地工作。 

---

目前，claude code的提示似乎不生效了：尽管会话结束，仍然收不到vibe notification的通知。 这是为什么？ 使用 awesome-code skill 辅助规划、优化。所有问题都要解决。 如果工作时有疑问，或者有更好的方案，自己选个最优方案优化，不要问我。不要破坏其它功能。要保证最终成品能正常、稳定、高效地工作。 

---

目前，claude code的提示似乎不生效了：尽管会话结束，仍然收不到vibe notification的通知。 这是为什么？ 使用 awesome-code skill 辅助规划、优化。所有问题都要解决。 如果工作时有疑问，或者有更好的方案，自己选个最优方案优化，不要问我。不要破坏其它功能。要保证最终成品能正常、稳定、高效地工作。 

---

最近codex更新后，又再次出现之前的bug——切实接收了用户的指令后vibenotification也会发送通知，而不是等会话结束了才发送通知。请：

- 联网了解codex的通知方式是不是有所更新
- 对因处理——优化vibenotification以适应最新的codex特性
- 我希望：会话结束了才发送通知

使用 awesome-code skill 辅助规划、优化。所有问题都要解决。 如果工作时有疑问，或者有更好的方案，自己选个最优方案优化，不要问我。不要破坏其它功能。要保证最终成品能正常、稳定、高效地工作。 

---

目前，codex切实接收了用户的指令后vibenotification也会发送通知，这是我不想要的。 我只希望会话结束了才发送通知。 要怎么做？

---

最近codex更新了，旧的报告方式存在误报的情况（明明不是会话结束，但却进行了报告）。 我用的codex版本是 `codex-cli 0.116.0`。请你：

- 联网彻底了解这个版本，怎么样才算“会话结束”。因为，现在有很多东西和“会话结束”类似，比如
  - codex切实接收了用户的指令
  - codex开了一个子agent
- 基于真实的“会话结束”信号，优化目前的报告方式。 

使用 awesome-code skill 辅助规划、优化。所有问题都要解决。 如果工作时有疑问，或者有更好的方案，自己选个最优方案优化，不要问我。不要破坏其它功能。要保证最终成品能正常、稳定、高效地工作。 

---

最近codex更新了一些东西，导致本项目的过度报告：

- 当用户向codex里发送一个prompt后，codex接收到就会立即响一次； 这不是我想要的。 我想要的，是当codex返回结果并结束时才触发响（因为用户只关心什么时候结束，并不关心什么开始）。

问题出在哪？