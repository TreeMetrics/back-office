# Multi-Agent Coordination Repository (GitHub-First)

You are working in a **multi-agent coordination repository** that uses **GitHub Issues as the source of truth** for task tracking.

## 🎯 Essential Context

**What this repository does:**
- Tracks all active tasks as GitHub Issues
- Coordinates multiple agents working simultaneously
- Uses GitHub labels for status/priority/type
- Stores local work state in `local-work.json` (gitignored, in repo root)
- Tracks time spent on tasks (syncs to GitHub Project board if configured)

**Your role:** You are one of potentially several agents working on different tasks. This repository may be used by multiple team members, each running their own agents, all coordinating via shared GitHub Issues.

## 🚀 Quick Start

**Essential reading:**
```bash
cat shared-workspace/GITHUB-FIRST-WORKFLOW.md
cat BRANCH-AND-WORKTREE-GUIDANCE.md  # When/how to create worktrees
```

**Typical workflow for code changes:**
```bash
# From coordination repo root:

# 1. List available tasks
./shared-workspace/shared-resources/scripts/gh-list-tasks.py --status planned

# 2. Start a task (starts time tracking automatically)
./shared-workspace/shared-resources/scripts/gh-start-task.py <issue-num> --agent <your-agent-id>

# 3. Create branch with worktree (standard for code changes)
./shared-workspace/shared-resources/scripts/gh-create-branch.py <issue-num> --repo backend --worktree -d "brief_description"
# Creates worktree at: ~/workspace/backend_dev/<project>_<issue-num>

# 4. Work in your worktree (use FULLY EXPANDED paths for file operations)
# Read/Edit/Write tools require paths like /home/username/workspace/..., NOT ~/workspace/...
# git add . && git commit && git push (from worktree)

# 5. Create PR (run from worktree with absolute path to script - see Rule 6)
<coordination-repo>/shared-workspace/shared-resources/scripts/gh-create-pr.py <issue-num> --title "Brief description"

# 6. Release your agent (from coordination repo)
./shared-workspace/shared-resources/scripts/gh-release-agent.py <your-agent-id>
```

**For coordination-only tasks (no code changes):**
```bash
# Just start the task, no branches needed
./shared-workspace/shared-resources/scripts/gh-start-task.py <issue-num> --agent <your-agent-id>
```

## 📋 Core Scripts

Located in `shared-workspace/shared-resources/scripts/`. Examples below show `./script.py` for brevity; when running from coordination repo root, use the full relative path: `./shared-workspace/shared-resources/scripts/script.py`

### Essential Scripts

1. **gh-create-issue.py** - Create GitHub issue with automatic project board addition
   ```bash
   ./gh-create-issue.py --title "Fix diameter units bug" --labels "status:triage,priority:high,type:bug"
   ./gh-create-issue.py --title "Add feature" --body "Detailed description" --assignee @me
   # With planning info:
   ./gh-create-issue.py --title "Feature X" --estimate 8 --start monday --target friday --milestone "v2.0"
   ```

   What it does:
   - Creates GitHub issue in coordination repo (or specified repo)
   - Automatically adds issue to project board (if project_board_id configured)
   - Supports labels, assignee, custom body
   - Supports planning: `--estimate` (hours), `--start` (date), `--target` (date), `--milestone`
   - Date formats: `2026-01-15`, `today`, `+7d`, `+2w`, `monday`, `friday`
   - Works for both coordination and code repositories

2. **gh-list-tasks.py** - List GitHub issues with local agent state
   ```bash
   ./gh-list-tasks.py                    # All open issues
   ./gh-list-tasks.py --status planned   # Filter by status
   ./gh-list-tasks.py --available        # Unassigned only
   ```

3. **gh-start-task.py** - Start or resume working on an issue (idempotent)
   ```bash
   ./gh-start-task.py 7 --agent yourname-task-description
   ./gh-start-task.py 7 --agent yourname-task-description --repo tm_api --worktree  # With branch+worktree
   ```

   What it does:
   - Assigns issue to you on GitHub
   - Updates status label to `in-progress`
   - **Auto-sets start_date to today** (if not already set) for roadmap visualization
   - Optionally creates linked branch and worktree
   - Starts time tracking session
   - Saves to local work state (`local-work.json`)
   - Safe to re-run (idempotent) - resumes existing work

4. **gh-create-branch.py** - Create linked branch for issue
   ```bash
   ./gh-create-branch.py 7 --repo backend
   ./gh-create-branch.py 7 --repo backend --worktree  # With worktree
   ```

   What it does:
   - Creates branch linked to issue via `gh issue develop`
   - Resolves repo shortname from config (backend → Org/backend)
   - Auto-detects default branch (master vs main)
   - Optionally creates worktree at conventional path
   - Can be called multiple times for multi-repo tasks

5. **gh-create-pr.py** - Create PR from current branch
   ```bash
   # Run from your code repository (worktree)
   ./gh-create-pr.py 7 --title "Add user authentication"
   ```

   - Creates PR via gh CLI
   - PR automatically links to issue (if branch created via gh-start-task.py)
   - Updates issue status to `ready-for-review`

6. **gh-query-prs.py** - Show PRs linked to an issue
   ```bash
   ./gh-query-prs.py 7
   ./gh-query-prs.py 7 --verbose
   ```

7. **gh-pr-status.py** - Show PR review status
   ```bash
   ./gh-pr-status.py                              # PRs for coordination issues
   ./gh-pr-status.py --global --reviewer @me      # Your review queue (all repos)
   ./gh-pr-status.py --global --reviewer alice    # Someone else's queue
   ./gh-pr-status.py --stale 7                    # PRs inactive 7+ days
   ```

8. **gh-update-status.py** - Update issue status and project fields
   ```bash
   ./gh-update-status.py 7 ready-for-review
   ./gh-update-status.py 7 in-progress --target friday    # Status + target date
   ./gh-update-status.py 7 --start today --target "+5d"   # Dates only (no status change)
   ./gh-update-status.py 7 --estimate 4                   # Estimate only
   ```

   - Status is optional if updating dates/estimate
   - Date formats: `2026-01-15`, `today`, `+7d`, `+2w`, `monday`, `friday`

9. **gh-release-agent.py** - Release your agent when done
   ```bash
   ./gh-release-agent.py my-agent-1
   ./gh-release-agent.py my-agent-1 --no-sync  # Skip GitHub time sync
   ```

   What it does:
   - Stops active time tracking session (calls gh-stop-work internally)
   - Syncs logged time to GitHub Project (if configured)
   - Releases agent from local work state

### Time Tracking Scripts

10. **gh-stop-work.py** - Stop work session without releasing agent
   ```bash
   ./gh-stop-work.py 7              # Stop session, sync to GitHub Project
   ./gh-stop-work.py 7 --no-sync    # Stop session without syncing
   ```

   Note: Usually you should use `gh-release-agent.py` instead, which calls this internally.
   Use this directly only if you need to check/sync time mid-session without releasing.

11. **gh-sync-time.py** - Manual time sync utility
   ```bash
   ./gh-sync-time.py 7 --show       # View current values (local vs GitHub)
   ./gh-sync-time.py 7              # Sync local time to GitHub Project
   ./gh-sync-time.py 7 --hours 2.5  # Manually set logged time
   ```

## 🚨 Critical Rules

### 0. Verify Before Acting

- **Verify current state before acting:** Read actual code, check actual files, run actual commands. Don't rely on assumptions, mental models, or unverified documentation. Exception: user-approved plans and user-confirmed information have already been verified.

### 1. GitHub Issues Are the Source of Truth

- **All task information lives on GitHub** (assignees, status, priority, PRs)
- **Local work state (`local-work.json`) is for agent coordination and time tracking**
- Time tracking syncs to GitHub Project board (if configured)
- Never try to edit GitHub issues manually via API - use the scripts

### 2. Status Labels

Valid status labels (TreeMetrics 8-state workflow):
- `status:triage` - New issue, needs initial assessment
- `status:ready` - Assessed and ready to start work
- `status:in-progress` - Actively implementing
- `status:ready-for-review` - PR created, awaiting code review
- `status:review` - Code review in progress
- `status:ready-to-test` - PR merged, awaiting deployment and QA
- `status:testing` - QA actively testing
- `status:blocked` - Cannot proceed (can happen at any stage)
- `status:done` - Released to production

Most status transitions are handled automatically by scripts (`gh-start-task.py` sets `in-progress`, `gh-create-pr.py` sets `ready-for-review`). The one agents must handle manually: if you can't proceed on a task, set it to blocked and explain why:
```bash
./shared-workspace/shared-resources/scripts/gh-update-status.py <num> blocked
# Add a comment explaining what's blocking (use full cross-repo refs per Rule 10)
gh issue comment <num> --body "Blocked: needs schema changes merged first (Org/backend#5)"
```
To resume from blocked, re-run `gh-start-task.py` (resets to `in-progress`).

### 3. Priority Labels (Triage/Planning Only)

Priority labels are used during **triage and sprint planning** to filter the backlog:
- `priority:high` - Should be addressed in current or next sprint
- `priority:medium` - Should be addressed within the quarter
- `priority:low` - Nice to have, address when capacity allows

**Design rationale:** Priority labels are an *input* to planning decisions, not a tracked field. Once an issue is scheduled, target dates and milestones supersede priority for execution. Priority labels:
- Help filter the backlog: `./shared-workspace/shared-resources/scripts/gh-list-tasks.py --status ready --priority high`
- Remain as historical context on issues
- Are **not** synced to the project board (dates/milestones serve that role)

```bash
# Triage: set priority
gh issue edit <num> --add-label "priority:high"

# Sprint planning: filter by priority, then set dates
./shared-workspace/shared-resources/scripts/gh-list-tasks.py --status ready --priority high
./shared-workspace/shared-resources/scripts/gh-update-status.py <num> --target friday --estimate 4
```

### 4. Agent Assignment

- Choose a **unique, descriptive agent-id** that includes your username to avoid collisions with other team members:
  - ✅ Good: `alice-auth-impl`, `bob-database-fix`, `yourname-feature-x`
  - ❌ Bad: `agent1`, `temp`, `auth-impl` (could collide with teammate's agent)
- Check if agent is already busy: `./shared-workspace/shared-resources/scripts/gh-list-tasks.py`
- Release agent when done: `./shared-workspace/shared-resources/scripts/gh-release-agent.py <agent-id>`
- **Important:** If working on a multi-user team, always include your username in agent-ids

### 5. Worktree Workflow

**Standard practice:** Always use worktrees for code changes (unless explicitly given permission to use primary repository).

**In worktrees (standard):**
- ✅ Make all code changes
- ✅ Git commits and pushes
- ✅ Create PRs from worktree
- ❌ NEVER run tests (let CI handle it)
- ❌ NEVER run database migrations (requires primary repo)

**⚠️ MIGRATIONS REQUIRE EXTRA STEPS:**
If your changes include a database migration file, you MUST:
1. Create and commit the migration file in your worktree
2. Push the branch
3. Ask the user to run the migration in the primary repo (or get permission to do it yourself)
4. The migration MUST be run before creating the PR - otherwise CI will fail due to schema.rb being out of sync

**Do NOT create a PR until the migration has been run and schema.rb is committed.**

See BRANCH-AND-WORKTREE-GUIDANCE.md "Scenario 2: Feature + Migration" for the complete workflow.

**Primary repository (requires explicit permission):**
- Only with developer permission AND verification of clean state
- Valid reasons: database migrations, debugging tests locally
- Must verify: clean git state, no other agents working
- See BRANCH-AND-WORKTREE-GUIDANCE.md for full details

**⚠️ PATH EXPANSION IN TOOL CALLS:**
When using Read/Edit/Write tools, use **fully expanded paths** starting with `/home/...`, NOT tilde paths. Tilde is expanded in shell commands but may not be expanded in tool call arguments.

### 6. PR Creation

Run `gh-create-pr.py` from your **worktree** (the script detects repo type from current directory). When running from outside the coordination repo, use an absolute path to the scripts directory:

```bash
# From worktree, use absolute path (substitute your actual coordination repo path)
<coordination-repo>/shared-workspace/shared-resources/scripts/gh-create-pr.py 7 --title "Description"
```

The script automatically uses "Related to" linking (won't auto-close issues). Only override with `--body "Closes #X"` if the issue is 100% complete after merge.

### 7. Command Permissions

Shared permissions are in `.claude/settings.json` (coordination scripts, git, read-only `gh`). Local permissions (including paths to code repositories from `project-local.yaml`) should be added to `.claude/settings.local.json`.

**Compound commands will prompt** (by design): `cd foo && ./script.py`, `for i in ...`. Run scripts from repo root using relative paths (e.g., `./shared-workspace/shared-resources/scripts/gh-list-tasks.py`) to avoid prompts.

### 8. Multi-Repo Tasks

For tasks spanning multiple repositories:

```bash
# From coordination repo root:

# 1. Start task (no branches created yet)
./shared-workspace/shared-resources/scripts/gh-start-task.py 7 --agent yourname-multi-repo-task

# 2. Create branches with worktrees
./shared-workspace/shared-resources/scripts/gh-create-branch.py 7 --repo backend --worktree
./shared-workspace/shared-resources/scripts/gh-create-branch.py 7 --repo frontend --worktree
# Creates worktrees at: ~/workspace/backend_dev/project_7, etc.

# 3. Work in each worktree (use /home/... paths in tool calls, not ~/...)
# Commit and push from within each worktree

# 4. Create PRs (must run from worktree - see Rule 6)
cd ~/workspace/backend_dev/project_7
<coordination-repo>/shared-workspace/shared-resources/scripts/gh-create-pr.py 7 --title "Part 1: Backend changes"

cd ~/workspace/frontend_dev/project_7
<coordination-repo>/shared-workspace/shared-resources/scripts/gh-create-pr.py 7 --title "Part 2: Frontend changes"

# 5. Check linked PRs (from coordination repo)
./shared-workspace/shared-resources/scripts/gh-query-prs.py 7
```

### 9. Use Coordination Scripts for Write Operations

For **read-only** queries, raw `gh` commands are fine:
```bash
gh issue view 51        # ✅ OK - reading
gh pr list              # ✅ OK - reading
```

For **write operations**, always use coordination scripts:

| Operation | Use This | NOT This |
|-----------|----------|----------|
| Create issue | `./gh-create-issue.py` | `gh issue create` |
| Create PR | `./gh-create-pr.py` | `gh pr create` |
| Start work | `./gh-start-task.py` | `gh issue edit --add-assignee` |
| Update status | `./gh-update-status.py` | `gh issue edit --add-label` |
| Create branch | `./gh-create-branch.py` | `git checkout -b` / `gh issue develop` |

**Why:** Scripts handle issue↔PR linking, status transitions, project board updates, local work state, and time tracking. Bypassing them breaks coordination.

### 10. Cross-Repo References

When writing comments or PR descriptions, always use full `Owner/Repo#Number` notation:

```bash
# ✅ Correct - explicit repo
Fixed in TreeMetrics/tm_api#1375
See TreeMetrics/ember-forest#471 for frontend

# ❌ Wrong - links to coordination repo
Fixed in #1375
```

Also applies to releases: say `tm_api v5.27.0`, not just `v5.27.0`.

**Why:** GitHub interprets `#N` relative to the current repo. In a coordination repo tracking multiple code repos, shorthand creates broken links.

### 11. Start Tasks Immediately

When a user says "resume", "work on", or "start" an issue, run `gh-start-task.py` **FIRST**:

```bash
# FIRST action - before checking status, before asking questions
./shared-workspace/shared-resources/scripts/gh-start-task.py 16 --agent yourname-task-description

# THEN investigate, ask questions, check status
```

**Why:** The script is idempotent (safe to re-run). Starting immediately ensures time tracking begins and other agents see the work in progress. Investigating first often leads to forgetting to start the task.

## ⚙️ Project Configuration

Configuration is split between two files:
- `project-shared.yaml` - Team-wide settings (committed to git)
- `project-local.yaml` - Your local paths and preferences (gitignored)

See `project-local.yaml.template` for setup instructions, including:
- Local filesystem paths for code repositories
- Worktree parent directories
- **Claude Code permissions for worktree editing** (section 7)

## 📄 Per-Issue Documentation

For complex tasks requiring planning, architecture docs, or review materials:

### Directory Structure

| Location | Purpose | Committed? |
|----------|---------|------------|
| `personal/<num>-<desc>/` | Working docs, drafts, preparation | No (gitignored) |
| `shared-workspace/docs/<num>-<desc>/` | Docs ready for review (active issues) | Yes |
| `shared-workspace/reference/` | Permanent docs (ADRs, guides) | Yes |

### Naming Convention
`<num>-<short-desc>` — e.g., `16-baseline-activities`, `42-auth-refactor`

### Lifecycle
1. Start working docs in `personal/<num>-<short-desc>/`
2. Move to `shared-workspace/docs/<num>-<short-desc>/` when ready for review
3. **On issue closure: DELETE the directory** (git history preserves if needed)
4. If docs have permanent value → move to `shared-workspace/reference/` first

**Policy:** Delete by default, preserve intentionally. No archive directory.

See `shared-workspace/docs/README.md` for full conventions.

## 🤖 Multi-Agent Coordination

**Before starting work:**
1. Check if task already has an agent: `./shared-workspace/shared-resources/scripts/gh-list-tasks.py`
2. Choose a unique agent-id (include your username if working with a team): `yourname-feature-impl`, `alice-bugfix`, etc.
3. Start task: `./shared-workspace/shared-resources/scripts/gh-start-task.py <issue-num> --agent <your-agent-id>`

**Agent-id collision?** The script will detect and warn you. If working on a team, always include your username to prevent collisions with teammates' agents.

**Worktree Edit/Write permissions:** Run `/apply-upgrade` after configuring `project-local.yaml` to add Edit/Write allow patterns and `additionalDirectories` to `.claude/settings.local.json`. Without this, agents get prompted for every file edit in worktrees. The `/add-dir` command only grants Read access for the current session.

## 🔐 Production Environment Access

**Default approach:** Ask the human how they access production, then provide commands for them to review and run manually.

**NEVER run without human confirmation:** DELETE/DROP operations, bulk updates (>10 records), schema migrations, `rm`/`mv` in production, service restarts.

**OK to provide for human review:** SELECT queries, COUNT operations, log inspection, status checks.

**Example - destructive operation:**
```
Task: "Delete inactive users from production"
Agent: "⚠️ This will DELETE records. How do you access production?"
Human: "AWS Session Manager"
Agent: "First, check how many: User.where(active: false, last_login: ...1.year.ago).count"
Human: "47"
Agent: "This will delete 47 users. Command:"
Agent: "  User.where(active: false, last_login: ...1.year.ago).destroy_all"
Agent: "Review carefully and run if correct."
```

If human has no access, provide the command and offer to create a GitHub issue to track it.

## 💡 Claude Code Best Practices

### Managing Context in Long Sessions

Context compaction happens automatically as conversations grow. To avoid losing important information:

- **Use subagents for exploration** - The Task tool with `subagent_type=Explore` runs investigation in isolated context. Results return as a summary without bloating your main conversation.
- **Run `/clear` between unrelated tasks** - Start fresh rather than accumulating stale context from previous work.
- **Stable instructions belong in CLAUDE.md** - This file reloads at session start and survives compaction. Conversation history does not.
- **Use skills for reusable workflows** - Skills in `.claude/skills/` load on demand rather than sitting in context.

The goal is keeping the main conversation focused on the current task.

### Plan Mode for Complex Tasks

For complex tasks, architectural decisions, or multi-step implementations, use **Plan mode** before implementing:

1. Press **Shift+Tab twice** to enter Plan mode
2. Iterate on the plan until the approach is solid
3. Get user approval, then switch to implementation

A good plan prevents wasted effort and ensures alignment before code is written.

### Pre-PR Linting

The `gh-create-pr.py` script runs linting/formatting checks before creating a PR:

- **Rails repos:** `bundle exec rubocop -a`
- **Node repos:** `npm run lint`
- **Python repos:** `ruff check . --fix && ruff format .`

The script detects repo type from marker files (Gemfile, package.json, pyproject.toml). Verification is off by default (worktrees lack dependencies); use `--verify` to enable if your environment supports it.

This catches style issues before CI but is not a substitute for test verification. Full test suites require database access, so leave those to CI. Worktrees are intentionally lightweight.

### PostToolUse Hooks (Code Repos)

Code repositories can auto-format files after edits by adding hooks to `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{"type": "command", "command": "prettier --write $FILE || true"}]
    }]
  }
}
```

Each code repo should configure its own formatter (prettier, rubocop, ruff, etc.). This reduces CI failures from formatting issues.

## ⚠️ Remember

- **Use scripts, not manual GitHub edits** (scripts keep local state in sync)
- **Release agent-id when done** (prevents collisions)
- **Create PRs from worktree** (not coordination repo)
- **Let GitHub track PRs** (automatic via linked branches)

## 📚 Additional Resources

**Complete workflow guide:**
```bash
cat shared-workspace/GITHUB-FIRST-WORKFLOW.md
```

**Project config:**
```bash
cat project-shared.yaml    # Team settings
cat project-local.yaml     # Your local settings
```

---

**Philosophy:** GitHub Issues are the shared source of truth. Local work state (`local-work.json` in repo root) coordinates which agents are working on what and tracks time spent. Everything else lives on GitHub.
