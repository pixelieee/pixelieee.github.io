# Hermes 自带 Kanban：先记下这个研究入口

> 待研究 · 根据官方文档整理，尚未完成实际运行验证。

Hermes 的 **Kanban (Multi-Agent Board)** 用任务看板协调多个 profile。任务可以分给不同的 Agent worker，交接和进度保存在数据库里。

## 三个入口，同一块看板

- **Dashboard**：在界面里查看任务状态。
- **CLI**：通过 `hermes kanban` 命令管理任务。
- **Worker tools**：Agent 用 `kanban_show`、`kanban_request_review`、`kanban_complete` 等工具读取任务、提交审查和报告完成。

[官方 Kanban 说明](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban)

## 下一步想验证什么

做一个小实验：让 `coder` 实现一个功能，交给 `reviewer` 审查，发现问题后退回修改。

1. 任务分给哪个 profile，由哪个步骤启动 worker？
2. 交接时传递哪些文件、消息和任务状态？
3. worker 失败或进程退出后，任务如何恢复？
4. 人工审查放在哪里，怎样判断任务真正完成？

这些问题先保留，跑过实验后再补结论。入口：[官方 Kanban tutorial](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban-tutorial)。
