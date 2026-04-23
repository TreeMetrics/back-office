# GitHub-First Coordination Workflow

**Status**: ✅ Tested and Validated (2025-11-14)

This directory contains scripts for a simplified GitHub-first coordination workflow that uses GitHub Issues as the source of truth instead of maintaining a git-committed `tasks.json` file.

## Overview

**Key Principle**: GitHub Issues are the source of truth for task tracking. Local state (agent assignments, time tracking) is stored in `local-work.json` at the repo root (gitignored).

## Architecture

```
GitHub Issues (shared, source of truth)
├─ Task tracking
├─ User assignment (assignees)
├─ Status tracking (labels: status:*, priority:*, type:*)
├─ Automatic PR linking (via gh issue develop)
└─ Comments, discussions, history

local-work.json (repo root, gitignored)
├─ Agent assignments (which local Claude agent is working)
├─ Time tracking sessions
└─ Working directories
```

## Scripts

All scripts are in `shared-workspace/shared-resources/scripts/`. Run from repo root using relative paths:

### Core Workflow

1. **gh-create-issue.py** - Create issue with automatic project board addition
   ```bash
   ./shared-workspace/shared-resources/scripts/gh-create-issue.py --title "Fix diameter units bug" --labels "status:triage,priority:high,type:bug"
   ./shared-workspace/shared-resources/scripts/gh-create-issue.py --title "Add feature" --body "Detailed description" --assignee @me
   ```

   What it does:
   - Creates GitHub issue in coordination repo (or specified repo via --repo)
   - Automatically adds to project board (if project_board_id configured)
   - Supports labels, assignee, custom body
   - Works for agent-created issues (not just manual GitHub issue creation)

2. **gh-list-tasks.py** - List issues with local agent state
   ```bash
   ./shared-workspace/shared-resources/scripts/gh-list-tasks.py                    # All open issues
   ./shared-workspace/shared-resources/scripts/gh-list-tasks.py --status planned   # Filter by status
   ./shared-workspace/shared-resources/scripts/gh-list-tasks.py --available        # Unassigned only
   ```

3. **gh-start-task.py** - Start working on an issue
   ```bash
   ./shared-workspace/shared-resources/scripts/gh-start-task.py 8 --agent my-agent-1
   ```

   What it does:
   - Assigns issue to you on GitHub
   - Updates status to `in-progress`
   - Saves to local state

4. **gh-create-branch.py** - Create linked branch for issue
   ```bash
   ./shared-workspace/shared-resources/scripts/gh-create-branch.py 8 --repo backend
   ./shared-workspace/shared-resources/scripts/gh-create-branch.py 8 --repo frontend --worktree
   ```

   What it does:
   - Creates branch linked to issue via `gh issue develop`
   - Resolves repo shortname from config (backend → Org/backend)
   - Auto-detects default branch (master vs main)
   - Optionally creates worktree at conventional path
   - Can be called multiple times for multi-repo tasks

5. **gh-update-status.py** - Update issue status
   ```bash
   ./shared-workspace/shared-resources/scripts/gh-update-status.py 8 ready-for-review
   ```

6. **gh-create-pr.py** - Create PR from current branch
   ```bash
   # Run from worktree, use absolute path to script
   /path/to/coordination-repo/shared-workspace/shared-resources/scripts/gh-create-pr.py 8 --title "Add authentication"
   ```

   Must be run from the code repository (e.g., worktree).
   PR automatically links to issue if branch was created via `gh issue develop`.

7. **gh-query-prs.py** - Show all PRs linked to an issue
   ```bash
   ./shared-workspace/shared-resources/scripts/gh-query-prs.py 8
   ./shared-workspace/shared-resources/scripts/gh-query-prs.py 8 --verbose
   ```

8. **gh-release-agent.py** - Release agent when done
   ```bash
   ./shared-workspace/shared-resources/scripts/gh-release-agent.py my-agent-1
   ```

### Helper Libraries

- **local_state.py** - Manages `local-work.json` state
- **gh_helpers.py** - GitHub API operations via `gh` CLI

## Configuration

See `project-shared.yaml` at repository root (local paths go in `project-local.yaml`):

```yaml
project:
  name: "Project Name"

  coordination_repo:
    github: "Org/repo"
    branch: "main"

  github:
    enabled: true
    org: "Org"

  label_mappings:
    status:
      - planned
      - in-progress
      - ready-for-review
      - completed
    priority:
      - high
      - medium
      - low
```

Local filesystem paths (worktree directories, repo locations) are configured separately in `project-local.yaml`. See `project-local.yaml.template` for setup.

## Benefits Over tasks.json Approach

1. ✅ **No git sync overhead** - No committing/pushing task state after every update
2. ✅ **Single source of truth** - GitHub Issues, not duplicate JSON file
3. ✅ **Native multi-repo PRs** - Automatic linking via `gh issue develop`
4. ✅ **Better visibility** - Everyone uses GitHub UI naturally
5. ✅ **Simpler** - Less infrastructure to maintain
6. ✅ **Aligned with Anthropic** - Matches Claude Code team collaboration patterns

## Trade-offs

- Requires internet connection (GitHub API dependency)
- GitHub rate limits: 5000 requests/hour (authenticated)
- Less suitable for fully offline work

## Example Workflow

```bash
# From coordination repo root:

# 1. See available tasks
./shared-workspace/shared-resources/scripts/gh-list-tasks.py --status planned

# 2. Start task #8
./shared-workspace/shared-resources/scripts/gh-start-task.py 8 --agent auth-impl

# 3. Create branch in needed repo(s)
./shared-workspace/shared-resources/scripts/gh-create-branch.py 8 --repo backend --worktree
# Creates branch and worktree at ~/workspace/backend_dev/project_8

# 4. Work on task (in worktree)
cd ~/workspace/backend_dev/project_8
# ... make changes ...
git add . && git commit -m "Implement auth"
git push

# 5. Create PR (from worktree, use absolute path to script)
/path/to/coordination-repo/shared-workspace/shared-resources/scripts/gh-create-pr.py 8 --title "Add authentication"
# PR automatically links to issue #8

# 6. Release agent (from coordination repo)
./shared-workspace/shared-resources/scripts/gh-release-agent.py auth-impl
```

## Validation

Tested 2025-11-14:
- ✅ Issue creation with labels
- ✅ gh-list-tasks.py with local state
- ✅ gh-start-task.py (assign, label, create linked branch)
- ✅ Automatic PR-to-issue linking
- ✅ gh-query-prs.py (cross-repo PR query)
- ✅ gh-release-agent.py (local state cleanup)

## Migration Path

For new projects:
1. Create project with GitHub Issues enabled
2. Use these scripts from day one
3. No tasks.json needed

For existing projects (optional):
- Can coexist with tasks.json approach
- Gradual migration possible
- Or keep tasks.json for historical reasons

## Future Use

This workflow is ready for:
- New coordination projects
- Teams that prefer GitHub-native workflows
- Projects where internet connectivity is reliable
