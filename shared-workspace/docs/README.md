# Per-Issue Documentation

This directory holds documentation for **active issues** that is ready for sharing, collaboration, or external review.

## Directory Structure

```
shared-workspace/docs/
├── README.md                       # This file
└── <num>-<short-desc>/             # Per-issue docs (ACTIVE issues only)
    ├── implementation-plan.md
    └── ...

personal/                           # Gitignored - working docs
└── <num>-<short-desc>/

shared-workspace/reference/         # Permanent docs (rare)
└── ...
```

## Conventions

### Naming
- Directory format: `<num>-<short-desc>` (e.g., `16-baseline-activities`, `42-auth-refactor`)
- No prescribed filenames — use whatever makes sense
- Common patterns: `implementation-plan.md`, `notes.md`, `architecture.md`

### When to Use Each Location

| Location | Purpose | Committed? |
|----------|---------|------------|
| `personal/<num>-<desc>/` | Working docs, drafts, preparation | No (gitignored) |
| `shared-workspace/docs/<num>-<desc>/` | Docs ready for review (active issues) | Yes |
| `shared-workspace/reference/` | Permanent docs (ADRs, guides) | Yes |

### Lifecycle

1. Start working docs in `personal/<num>-<short-desc>/`
2. Move/copy to `shared-workspace/docs/<num>-<short-desc>/` when ready for review
3. **On issue closure: DELETE the directory**
4. If docs have permanent value → move to `shared-workspace/reference/` before closing

### Garbage Collection Policy

**Delete by default, preserve intentionally.**

- Per-issue docs are deleted when the issue closes
- Git history preserves them if needed later
- Only truly permanent docs belong in `reference/`
- No archive directory — keeps working tree clean
