---
name: start-task
description: Start working on a GitHub issue (assigns, updates status, starts time tracking)
argument-hint: <issue-number> [--agent <agent-id>]
---

Start working on issue $ARGUMENTS.

Run this command from the repo root:

```bash
./shared-workspace/shared-resources/scripts/gh-start-task.py $ARGUMENTS
```

This auto-sets the issue status to `in-progress` and starts time tracking.

If no `--agent` was specified, choose a unique agent-id that includes your username to avoid collisions (e.g., `cian-feature-x`, `alice-bugfix`).

After starting, check if you need to create a branch/worktree for code changes:
- For code changes: `./shared-workspace/shared-resources/scripts/gh-create-branch.py <issue-num> --repo <repo> --worktree`
- For coordination-only tasks: No branch needed
