# GitHub-First Coordination Architecture

## Overview

This coordination system uses **GitHub Issues as the source of truth** for task tracking, with local metadata for agent coordination and time tracking.

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub Issues                             │
│  (Source of Truth)                                               │
│  - Task definition                                               │
│  - Status (via labels)                                           │
│  - Assignees                                                     │
│  - Linked PRs                                                    │
│  - Comments/discussions                                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ Linked to
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Project Board                          │
│  (Optional - Enhanced Tracking)                                  │
│  - Status columns                                                │
│  - Custom fields:                                                │
│    • Logged time (synced from local)                             │
│    • Planned time                                                │
│    • Priority, Type, etc.                                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ Time sync via GraphQL
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    local-work.json                               │
│  (Local Metadata - GITIGNORED)                                   │
│  Location: <coord-repo>/local-work.json                          │
│                                                                   │
│  Tracks per-issue:                                               │
│  - Agent assignment                                              │
│  - Code repo                                                     │
│  - Branch name                                                   │
│  - Worktree path                                                 │
│  - Working directory                                             │
│  - Time tracking:                                                │
│    • Sessions (start/end/minutes)                                │
│    • Total minutes                                               │
│    • Last GitHub sync                                            │
│  - GitHub Project item ID                                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ References
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Code Repositories (Worktrees)                       │
│                                                                   │
│  ~/workspace/tm_api_dev/                                         │
│  ├── tm_api/           ← Primary (has DB, configs)               │
│  ├── qarlbo_7/         ← Worktree for issue #7                   │
│  └── qarlbo_12/        ← Worktree for issue #12                  │
│                                                                   │
│  ~/workspace/ember-forest_dev/                                   │
│  ├── ember-forest/     ← Primary                                 │
│  └── qarlbo_7/         ← Worktree for issue #7 (multi-repo)      │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ Agent work happens here
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Coordination Repo Directories                       │
│                                                                   │
│  personal/              ← Local working files (GITIGNORED)       │
│  ├── qarlbo-7/                                                   │
│  │   ├── notes.md                                                │
│  │   ├── investigation.md                                        │
│  │   └── implementation-spec.md                                  │
│  └── qarlbo-12/                                                  │
│      └── draft-plan.md                                           │
│                                                                   │
│  Important/shareable files → Attach directly to GitHub issues    │
│  No intermediate committed directory needed                      │
│                                                                   │
│  shared-workspace/      ← Coordination infrastructure (COMMITTED)│
│  ├── shared-resources/scripts/  ← Coordination scripts           │
│  ├── shared-resources/templates/                                 │
│  └── ARCHITECTURE.md, docs, etc.                                 │
└─────────────────────────────────────────────────────────────────┘
```

## File Organization Philosophy

### Three Distinct Locations

1. **personal/** (gitignored, local only)
   - Your working notes, drafts, investigations
   - Disposable, never shared
   - Example: `personal/qarlbo-7/investigation.md`

2. **GitHub Issues** (attachments)
   - Important deliverables: specs, QA reports, implementation plans
   - Discussion and decisions
   - Files attached directly to relevant issue
   - Example: Attach `implementation-spec.md` to issue #7

3. **shared-workspace/** (committed, minimal)
   - Coordination infrastructure only
   - Scripts, templates, architecture docs
   - NOT issue-specific output
   - Example: `shared-workspace/ARCHITECTURE.md`

### Where Does Each File Type Go?

| File Type | Location | Why |
|-----------|----------|-----|
| Working notes | `personal/` | Local, disposable |
| Draft plans | `personal/` | Local until finalized |
| Implementation specs | Attach to GitHub issue | Shared, permanent |
| QA reports | Attach to GitHub issue | Shared, permanent |
| Investigation findings | Attach to GitHub issue | Shared, permanent |
| Code documentation | Code repo PR (docs/) | Belongs with code |
| Coordination scripts | `shared-workspace/shared-resources/scripts/` | Infrastructure |
| Architecture docs | `shared-workspace/` | Infrastructure |

**Key principle:** If it matters beyond your local work session, it goes on GitHub (issue attachment or code repo), not in a committed coordination directory.

## Naming Conventions

### Worktrees
**Format:** `{worktree_parent}/{coord_project}_{issue#}/`

**Examples:**
- `~/workspace/tm_api_dev/qarlbo_7/`
- `~/workspace/tm_api_dev/qarlbo_12/`
- `~/workspace/ember-forest_dev/qarlbo_7/`

**Rationale:**
- Parent directory (`tm_api_dev`) provides repo context
- Coordination project name (`qarlbo`) prevents collisions between projects
- Issue number (`7`) identifies the specific task

### Branches
**Format:** `{coord_project}_{issue#}_{description}`

**Examples:**
- `qarlbo_7_report_triggers`
- `qarlbo_12_user_authentication`

**Rationale:**
- Coordination project name prevents collisions
- Issue number provides traceability
- Description aids human readability

### Working Directories
**Format:** `personal/{coord_project}-{issue#}/`

**Examples:**
- `personal/qarlbo-7/`
- `personal/qarlbo-12/`

## Configuration Files

### project-shared.yaml (Committed)
Project-wide configuration shared across all developers:
- Coordination repo details
- GitHub organization and project board ID
- Project field IDs (status, time tracking)
- Code repository metadata (GitHub URLs, branches)
- Label mappings

**Key sections:**
```yaml
project:
  github:
    project_board_id: "PVT_kwDOAAzY884Arwin"
    project_fields:
      status:
        field_id: "PVTSSF_..."
        options:
          in-progress: "47fc9ee4"

code_repositories:
  - name: "tm_api"
    github: "TreeMetrics/tm_api"
    default_branch: "master"
```

### project-local.yaml (Gitignored)
Personal settings that differ per developer:
- Local filesystem paths to repositories
- Worktree parent directories

**Key sections:**
```yaml
code_repositories:
  - name: "tm_api"
    worktree_parent: "~/workspace/tm_api_dev"
    primary_dir_name: "tm_api"
```

### local-work.json (Gitignored)
Machine-local work metadata, never committed:
- Issue assignments
- Branch/worktree paths
- Time tracking sessions
- Working directory paths

## Key Scripts

### Core Workflow
1. **gh-start-task.py** - Start or resume work (idempotent)
2. **gh-stop-work.py** - Stop current session, sync time
3. **gh-create-pr.py** - Create PR, update status
4. **gh-release-agent.py** - Release agent, clean up local state
5. **gh-sync-time.py** - Manually sync time to GitHub Project

### Time Tracking Flow
```
Agent starts work
    ↓
gh-start-task.py creates session in local-work.json
    ↓
Agent works (time automatically tracked)
    ↓
gh-stop-work.py ends session, calculates minutes
    ↓
Time synced to GitHub Project "Logged time" field
    ↓
local-work.json records last sync time
```

## Primary Directory Special Status

The primary directory (e.g., `~/workspace/tm_api_dev/tm_api/`) is NOT a worktree:
- ✅ Contains development & test databases
- ✅ Has configuration files
- ✅ Used for running migrations
- ✅ Used for debugging (run specs locally)
- ⚠️ ONE agent at a time (requires coordination)
- ⚠️ Requires explicit approval before use

## Multi-Project Coordination

Multiple coordination projects can work on the same codebase simultaneously:

**Example:**
- `qarlbo` project, issue #7 → `~/workspace/tm_api_dev/qarlbo_7/`
- `hq-upgrades` project, issue #42 → `~/workspace/tm_api_dev/hq-upgrades_42/`

Both work on `tm_api` codebase, but separate worktrees prevent conflicts.

## GitHub Project Integration

**Prerequisites:**
1. Create GitHub Project board
2. Add custom fields for time tracking
3. Get field IDs: `gh project field-list <number> --owner <org>`
4. Configure in `project-shared.yaml`

**Time Sync:**
- Local sessions tracked automatically
- Synced to GitHub Project "Logged time" field
- Visible in project board
- Aggregatable across issues

## Benefits

1. **GitHub Issues as source of truth** - Single authoritative location
2. **No git push/pull overhead** - Local metadata not committed
3. **Automatic time tracking** - Sessions tracked locally
4. **GitHub Project visibility** - Time synced for reporting
5. **Multi-project support** - Naming conventions prevent collisions
6. **Flexible naming** - Developers can use custom names, stored in metadata
7. **Idempotent operations** - Scripts handle both fresh start and resume

## Migration from Old System

Old coordination-template (tasks.json) → New github-first:

| Feature | Old (tasks.json) | New (github-first) |
|---------|------------------|-------------------|
| Task registry | tasks.json (committed) | GitHub Issues |
| Status tracking | tasks.json | GitHub labels |
| Agent assignment | tasks.json | local-work.json (gitignored) |
| Time tracking | tasks.json | local-work.json + GitHub Project |
| PR tracking | tasks.json | Automatic via gh issue develop |
| Working files | shared-workspace/agent-outputs/ | personal/ (local) + GitHub attachments |
| Shareable docs | shared-workspace/agent-outputs/ | GitHub issue attachments |

**Key differences:**
1. Separation of shared state (GitHub) from local state (local-work.json)
2. No committed agent-outputs/ directory - use GitHub issue attachments instead
3. True github-first: GitHub is the source of truth, not the coordination repo
