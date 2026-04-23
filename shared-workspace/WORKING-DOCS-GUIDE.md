# Per-Issue Working Directories

## Directory Structure

```
personal/<issue-num>-<short-desc>/        # Working docs (gitignored)
shared-workspace/docs/<issue-num>-<desc>/ # Docs for review/collaboration (committed)
shared-workspace/reference/               # Permanent docs (ADRs, guides)
```

## Example: Issue #60 (Inventory Data Analysis)

**Personal (private working docs):**
```
personal/60-data-analysis/
├── scratch-notes.md          # Raw exploration
├── poc-test-script.rb        # Throwaway code
└── test-data/                # Sample files
```

**Shared docs (ready for collaboration):**
```
shared-workspace/docs/60-data-analysis/
├── data-comparison.md        # Findings ready for review
└── proposed-schema.md        # Draft spec for feedback
```

**Reference (permanent):**
```
shared-workspace/reference/
├── fw-inventory-implementation-plan.md   # Current source of truth
├── fw-system-reference.md                # System documentation
├── adr-001-volume-storage-pattern.md     # Architectural decision record
└── fw-design-history/                    # Historical analysis
    ├── README.md
    ├── 01-data-investigation-findings.md
    ├── 02-comprehensive-data-comparison.md
    └── 03-architectural-options.md
```

## Lifecycle

| Stage | Location | Committed? |
|-------|----------|------------|
| 1. Active work | `personal/<num>-<desc>/` | No |
| 2. Review/collaboration | `shared-workspace/docs/<num>-<desc>/` | Yes |
| 3. Permanent value | `shared-workspace/reference/` | Yes |
| 4. Issue closed | Move valuable docs to `reference/`, then delete `personal/` and `docs/` dirs | N/A |

## When to Use Each

**`personal/`** (gitignored)
- Drafts, scratch work, exploration
- POC scripts and test data
- Anything not ready for others to see

**`shared-workspace/docs/`** (committed, temporary)
- Specs ready for review and/or collaboration
- Documentation for active issues that needs sharing with teammates or other agents
- Deleted when issue closes

**`shared-workspace/reference/`** (committed, permanent)
- ADRs, system references, guides
- Historical design records worth preserving
- Implementation plans

## Naming Convention

`<issue-num>-<short-desc>` — e.g., `60-data-analysis`, `84-client-reporting`, `75-mvp-design`
