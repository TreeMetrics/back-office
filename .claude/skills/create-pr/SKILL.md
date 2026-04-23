---
name: create-pr
description: Create a pull request linked to a GitHub issue
argument-hint: <issue-number> --title "<title>"
---

Create a PR for issue $ARGUMENTS.

Run this command from your **worktree** (not the coordination repo):

```bash
./shared-workspace/shared-resources/scripts/gh-create-pr.py $ARGUMENTS
```

Required: `--title "Brief description of changes"`

The script will:
- Run linting/formatting checks before creating the PR
- Create the PR via `gh pr create`
- Update issue status to `ready-for-review`
- PR automatically links to issue (if branch was created via gh-create-branch.py)

Note: Run from the code repository worktree where your changes are, not from the coordination repo.
