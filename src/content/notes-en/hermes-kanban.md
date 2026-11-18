---
title: "Hermes Kanban: Multi-Agent Dispatch and Handoff"
dek: "How a task board lets several Hermes profiles split the work, hand it off and send it back."
summary: "When several agents share the work, how does a task get handed out, handed back, and sent back again? Still reading the source; for now this is a list of what I want to find out."
date: "2026-11-16"
topic: "Agent engineering"
status: "todo"
---

Hermes's **Kanban (Multi-Agent Board)** coordinates several profiles through a task board. Tasks can be assigned to different agent workers, and handoffs and progress are kept in a database.

## Three entry points, one board

- **Dashboard**: view task status in the UI.
- **CLI**: manage tasks with the `hermes kanban` command.
- **Worker tools**: agents use tools such as `kanban_show`, `kanban_request_review` and `kanban_complete` to read tasks, request review and report completion.

[Official Kanban guide](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban)

## Dispatch, review and recovery

Take a flow where `coder` implements a feature and `reviewer` reviews it and sends it back for changes:

1. Which profile gets the task, and which step starts the worker?
2. What files, messages and task state are passed along in a handoff?
3. When a worker fails or its process exits, how is the task recovered?
4. Where does human review fit in, and how is a task judged truly done?

For the walkthrough, see the [official Kanban tutorial](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban-tutorial).
