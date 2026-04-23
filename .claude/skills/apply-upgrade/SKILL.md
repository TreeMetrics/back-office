---
name: apply-upgrade
description: Apply pending migrations after updating from coordination-template
argument-hint:
---

Apply any pending migrations/fixes after pulling updates from the coordination-template.

Run the upgrade script:

```bash
python3 .claude/skills/apply-upgrade/upgrade.py
```

## Current Migrations

### 2026-02-09: Edit/Write permissions for worktrees

Reads `worktree_parent` and `primary_dir_name` from `project-local.yaml` and adds to `.claude/settings.local.json`:
- **allow:** `Edit(~/worktree_parent/**)` and `Write(~/worktree_parent/**)` — agents can edit worktree files without prompts
- **deny:** `Edit(~/worktree_parent/primary_dir/**)` and `Write(~/worktree_parent/primary_dir/**)` — protects primary checkout from accidental edits

**Why needed:** `additionalDirectories` only grants Read access. Without explicit Edit/Write allow patterns, agents get prompted for every file edit in worktree directories. Deny rules for the primary checkout prevent agents from accidentally modifying the main branch.

### 2026-02-17: Bash script permissions with absolute paths

Reads relative-path `Bash(./...)` patterns from `.claude/settings.json` and creates absolute-path equivalents in `.claude/settings.local.json`. When agents call coordination scripts from worktrees using absolute paths (per Rule 6), the relative patterns don't match, causing permission prompts.

**Why needed:** The shared `settings.json` has relative patterns that only work from the coordination repo directory. Absolute-path patterns are machine-specific, so they belong in the local settings.

### 2026-01-31: additionalDirectories for background agents

Reads `worktree_parent` paths from `project-local.yaml` and adds them to `.claude/settings.local.json` as `additionalDirectories`. This grants Read access so background agents can navigate worktree directories.

**Why needed:** Background agents cannot prompt for directory permissions. Without this config, they fail with "Permission auto-denied" when reading files in worktrees outside the coordination repo.
