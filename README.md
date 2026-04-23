# Multi-Agent Coordination Template

**GitHub-first coordination system for multi-agent Claude Code projects.**

This system uses **GitHub Issues as the source of truth** for task tracking, with local state for agent coordination and time tracking.

> **Creating a new project from this template?** See the [Setup Guide](https://github.com/TreeMetrics/coordination-template-v2/wiki/Setup-Guide) in the wiki.

---

## Quick Start

```bash
cd shared-workspace/shared-resources/scripts

# List available tasks
./gh-list-tasks.py --status ready

# Start a task
./gh-start-task.py 1 --agent yourname-task

# Create branch with worktree (for code changes)
./gh-create-branch.py 1 --repo backend --worktree

# When done, create PR (from worktree)
./gh-create-pr.py 1 --title "Your PR title"

# Release agent
./gh-release-agent.py yourname-task
```

## Documentation

| Document | Purpose |
|----------|---------|
| **[GETTING-STARTED.md](GETTING-STARTED.md)** | How the system works and why |
| **[DEVELOPER-SETUP-ONEPAGE.md](DEVELOPER-SETUP-ONEPAGE.md)** | Quick setup for joining a project |
| **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** | Daily command cheat sheet |
| **[GITHUB-FIRST-WORKFLOW.md](shared-workspace/GITHUB-FIRST-WORKFLOW.md)** | Complete workflow guide |
| **[BRANCH-AND-WORKTREE-GUIDANCE.md](BRANCH-AND-WORKTREE-GUIDANCE.md)** | When/how to use worktrees |
| **[ARCHITECTURE.md](shared-workspace/ARCHITECTURE.md)** | System design and data flow |
| **[.claude/CLAUDE.md](.claude/CLAUDE.md)** | Agent instructions |

**Template-specific docs:** See the [wiki](https://github.com/TreeMetrics/coordination-template-v2/wiki) for project setup and onboarding templates.

## Core Scripts

All scripts in `shared-workspace/shared-resources/scripts/`:

| Script | Purpose |
|--------|---------|
| `gh-list-tasks.py` | List issues with local agent state |
| `gh-start-task.py` | Start work (assign, label, track time) |
| `gh-create-branch.py` | Create linked branch with optional worktree |
| `gh-create-pr.py` | Create PR with automatic issue linking |
| `gh-update-status.py` | Update issue status |
| `gh-query-prs.py` | Query linked PRs across repositories |
| `gh-release-agent.py` | Release agent, sync time |
| `gh-create-issue.py` | Create issues with project board integration |

## Prerequisites

- GitHub CLI (`gh`) installed and authenticated
- Python 3.7+ with PyYAML (`pip3 install pyyaml`)
- Git with worktree support

## Project Structure

```
coordination-repo/
├── .claude/
│   └── CLAUDE.md                    # Agent instructions
├── shared-workspace/
│   ├── GITHUB-FIRST-WORKFLOW.md     # Workflow documentation
│   ├── ARCHITECTURE.md              # System design
│   └── shared-resources/
│       └── scripts/                 # Coordination scripts
├── project-shared.yaml              # Shared config (GitHub IDs, labels)
├── project-local.yaml               # Local config (paths) - gitignored
└── local-work.json                  # Agent state, time tracking - gitignored
```

## License

This is a template repository. Use it for your projects freely.
