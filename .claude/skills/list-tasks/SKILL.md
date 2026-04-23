---
name: list-tasks
description: List GitHub issues with status and agent assignments
argument-hint: [--status <status>] [--available]
---

List tasks from GitHub Issues.

Run this command from the repo root:

```bash
./shared-workspace/shared-resources/scripts/gh-list-tasks.py $ARGUMENTS
```

Common options:
- No arguments: Show all open issues
- `--status planned`: Filter by status label
- `--available`: Show only unassigned issues
- `--priority high`: Filter by priority
