# 基本

创建tag v1.0.5， /git-commit。 然后，  /git-publish-release 。 

# 日常

---

最近codex更新了一些东西，导致本项目的过度报告：

- 当用户向codex里发送一个prompt后，codex接收到就会立即响一次； 这不是我想要的。 我想要的，是当codex返回结果并结束时才触发响（因为用户只关心什么时候结束，并不关心什么开始）。

问题出在哪？