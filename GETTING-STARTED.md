# Getting Started

## What Is This?

This is a **multi-agent coordination repository**. It uses GitHub Issues as the single source of truth for task management across multiple code repositories.

You have code in separate repos (e.g., `tm_api`, `ember-forest`), but track all work centrally here via GitHub Issues. Multiple agents (human or AI) can work simultaneously on different tasks without stepping on each other.

## Key Components

**GitHub Issues** — Every task is an issue with status labels (`status:triage` → `status:in-progress` → `status:ready-for-review` → ... → `status:done`) and priority labels for backlog filtering.

**GitHub Project Board** — The dashboard that ties everything together. Issues flow through status columns, time tracking is synced here, and start/target dates enable roadmap visualization. The scripts keep it updated automatically.

**Coordination Scripts** (`shared-workspace/shared-resources/scripts/`) — Python scripts that wrap `gh` CLI and keep everything in sync:
- `gh-start-task.py` — assigns you, sets status, starts time tracking
- `gh-create-branch.py` — creates a branch linked to an issue in a target code repo
- `gh-create-pr.py` — creates a PR that auto-links back to the issue
- `gh-release-agent.py` — stops time tracking, frees the agent slot

**local-work.json** — Gitignored file tracking which agents are working on what and their time sessions. This is the local coordination layer. If it disappears, GitHub still has the full picture.

**Worktrees** — Code changes happen in git worktrees (e.g., `~/workspace/tm_api_dev/project_7/`) rather than the primary repo checkouts, so multiple tasks can run in parallel without branch conflicts.

**Working Documents** — Three locations for per-issue docs: `personal/` for drafts (gitignored), `shared-workspace/docs/` for team review (committed), and `shared-workspace/reference/` for permanent guides. The agent follows these conventions automatically.

**Configuration** — Split between `project-shared.yaml` (team settings, committed) and `project-local.yaml` (your local paths, gitignored).

## Typical Flow

```
1. Pick an issue        →  gh-list-tasks.py --available
2. Claim it             →  gh-start-task.py 42 --agent cian-fix-bug
3. Create worktree      →  gh-create-branch.py 42 --repo tm_api --worktree
4. Code in worktree     →  edit, commit, push
5. Open PR              →  gh-create-pr.py 42 --title "Fix the bug"
6. Release agent        →  gh-release-agent.py cian-fix-bug
```

The scripts handle the glue: updating labels, linking PRs to issues, syncing time to the Project board, and preventing agent collisions.

## Why It Exists

It lets multiple agents (or humans) work on tasks across multiple repos without conflicting, while keeping GitHub as the place anyone can look to see what's happening. The local JSON file is just ephemeral coordination state — if it disappears, GitHub still has the full picture.

## Next Steps

**Set up:** [DEVELOPER-SETUP-ONEPAGE.md](DEVELOPER-SETUP-ONEPAGE.md) (2-3 minutes)

**Learn more:** The [wiki](https://github.com/TreeMetrics/coordination-template-v2/wiki) has deeper explanations of each component — the Project Board, working documents, configuration, and more.

**Reference:** [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for daily commands, [GITHUB-FIRST-WORKFLOW.md](shared-workspace/GITHUB-FIRST-WORKFLOW.md) for the full workflow guide.
