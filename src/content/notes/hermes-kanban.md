---
title: "Hermes Kanban：多 Agent 任务派发与交接"
titleEn: "Hermes Kanban: Multi-Agent Dispatch and Handoff"
summaryEn: "When several agents share the work, how does a task get handed out, handed back, and sent back again? Still reading the source; for now this is a list of what I want to find out."
summary: "几个 Agent 一起干活时，任务怎样派出去、做完怎样交回来、被退回时又发生了什么？这篇还在读源码，先把想弄清的问题记在这里。"
date: "2026-11-16"
topic: "Agent 工程"
status: "todo"
---

Hermes 的 **Kanban (Multi-Agent Board)** 用任务看板协调多个 profile。任务可以分给不同的 Agent worker，交接和进度保存在数据库里。

## 三个入口，同一块看板

- **Dashboard**：在界面里查看任务状态。
- **CLI**：通过 `hermes kanban` 命令管理任务。
- **Worker tools**：Agent 用 `kanban_show`、`kanban_request_review`、`kanban_complete` 等工具读取任务、提交审查和报告完成。

[官方 Kanban 说明](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban)

## 任务派发、审查与恢复

以 `coder` 实现功能、`reviewer` 审查并退回修改的流程为例：

1. 任务分给哪个 profile，由哪个步骤启动 worker？
2. 交接时传递哪些文件、消息和任务状态？
3. worker 失败或进程退出后，任务如何恢复？
4. 人工审查放在哪里，怎样判断任务真正完成？

相关流程参见：[官方 Kanban tutorial](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban-tutorial)。
