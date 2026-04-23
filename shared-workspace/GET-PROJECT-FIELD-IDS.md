# Getting GitHub Project Field and Option IDs

This guide shows how to get the field IDs and option IDs needed for `project-shared.yaml`.

---

## Prerequisites

- `gh` CLI installed and authenticated
- Access to the GitHub Project you want to configure

---

## Step 1: Get Project ID

List all projects for your organization:

```bash
gh project list --owner TreeMetrics
```

Output example:
```
13	SINTETIC	open	PVT_kwDOAAzY884Arwin
15	Qarlbo	open	PVT_kwDOAAzY884BGlyw
```

Copy the Project ID (e.g., `PVT_kwDOAAzY884Arwin`) - you'll need this for `project_board_id` in config.

---

## Step 2: Get Field IDs

List all fields for your project:

```bash
gh project field-list <project-number> --owner TreeMetrics
```

Example:
```bash
gh project field-list 13 --owner TreeMetrics
```

Output example:
```
Status          SELECT     PVTSSF_lADOAAzY884Arwinzgiyu7M
Logged time     NUMBER     PVTF_lADOAAzY884Arwinzgiyu8Q
Planned time    NUMBER     PVTF_lADOAAzY884Arwinzgiyu8U
```

Copy the field IDs:
- **Status field ID**: `PVTSSF_lADOAAzY884Arwinzgiyu7M`
- **Logged time field ID**: `PVTF_lADOAAzY884Arwinzgiyu8Q`
- **Planned time field ID**: `PVTF_lADOAAzY884Arwinzgiyu8U`

---

## Step 3: Get Status Option IDs

For single-select fields like Status, you need the option IDs. Use this GraphQL query:

```bash
gh api graphql -f query='
{
  node(id: "PROJECT_ID") {
    ... on ProjectV2 {
      field(name: "Status") {
        ... on ProjectV2SingleSelectField {
          id
          name
          options {
            id
            name
          }
        }
      }
    }
  }
}'
```

**Replace `PROJECT_ID`** with your actual project ID (e.g., `PVT_kwDOAAzY884Arwin`).

### Example

```bash
gh api graphql -f query='
{
  node(id: "PVT_kwDOAAzY884Arwin") {
    ... on ProjectV2 {
      field(name: "Status") {
        ... on ProjectV2SingleSelectField {
          id
          name
          options {
            id
            name
          }
        }
      }
    }
  }
}'
```

### Output Example

```json
{
  "data": {
    "node": {
      "field": {
        "id": "PVTSSF_lADOAAzY884Arwinzgiyu7M",
        "name": "Status",
        "options": [
          {"id": "f75ad846", "name": "Todo"},
          {"id": "ff7903a6", "name": "On Hold"},
          {"id": "47fc9ee4", "name": "In Progress"},
          {"id": "feee3889", "name": "Review"},
          {"id": "4fe0cea1", "name": "Ready for Release"},
          {"id": "b2b8379a", "name": "Testing"},
          {"id": "98236657", "name": "Done"}
        ]
      }
    }
  }
}
```

**Copy the option IDs** - you'll map these to your status names in config.

---

## Step 4: Update project-shared.yaml

Now fill in `project-shared.yaml` with the IDs you collected:

```yaml
github:
  project_board_id: "PVT_kwDOAAzY884Arwin"  # From Step 1

  project_fields:
    status:
      field_id: "PVTSSF_lADOAAzY884Arwinzgiyu7M"  # From Step 2
      options:
        # Map your status names to GitHub Project option IDs (from Step 3)
        triage: "f75ad846"           # Maps to "Todo"
        ready: "f75ad846"            # Maps to "Todo"
        in-progress: "47fc9ee4"      # Maps to "In Progress"
        ready-for-review: "feee3889" # Maps to "Review"
        review: "feee3889"           # Maps to "Review"
        ready-to-test: "4fe0cea1"    # Maps to "Ready for Release"
        testing: "b2b8379a"          # Maps to "Testing"
        blocked: "ff7903a6"          # Maps to "On Hold"
        done: "98236657"             # Maps to "Done"

    logged_time:
      field_id: "PVTF_lADOAAzY884Arwinzgiyu8Q"  # From Step 2

    planned_time:
      field_id: "PVTF_lADOAAzY884Arwinzgiyu8U"  # From Step 2
```

**Note:** Local filesystem paths (worktree directories, repo locations) go in `project-local.yaml`, not here. See `project-local.yaml.template` for setup.

---

## Mapping Notes

### Multiple Status Names → One Option

You can map multiple status names to the same option ID:

```yaml
triage: "f75ad846"  # Both map to "Todo"
ready: "f75ad846"   # Both map to "Todo"
```

This is useful when:
- Your workflow has more granular status labels than GitHub Project columns
- You want flexibility in status naming while keeping board simple

### Status Name Must Match Label Mappings

The status names in `project_fields.status.options` must match the status names in `label_mappings.status`:

```yaml
label_mappings:
  status:
    - in-progress      # ← Must have matching entry in project_fields
    - ready-for-review # ← Must have matching entry in project_fields
    # ... etc
```

---

## Testing Your Configuration

After updating the config, test it:

```bash
# Start a task (should update both label and project field)
./gh-start-task.py 7 --agent test-agent

# Check the issue on GitHub:
# - Label should be "status:in-progress"
# - Project board Status should be "In Progress"
```

If the project field doesn't update, check:
1. Is `project_board_id` set correctly?
2. Is the issue added to the project board?
3. Are the field IDs correct?
4. Are the option IDs correct?

Script output will show warnings if configuration is missing.

---

## Troubleshooting

### "Issue not in project board"

The issue must be added to the project board before field updates work.

**Add manually:**
1. Go to GitHub Project board
2. Click "+ Add item"
3. Search for your issue and add it

**Or use gh CLI:**
```bash
gh project item-add <project-number> --owner TreeMetrics --url https://github.com/TreeMetrics/coordination-template/issues/7
```

### "No option ID configured for status X"

You forgot to add a mapping for status `X` in `project_fields.status.options`.

Add it:
```yaml
status:
  options:
    X: "option_id_here"  # Find the right option ID from Step 3
```

### Field IDs don't work

Field IDs are project-specific. If you copied IDs from another project, they won't work. Re-run Steps 1-3 for YOUR specific project.

---

## Reference: Field ID Formats

- **Project ID**: `PVT_kwDO...` (starts with PVT)
- **Number field ID**: `PVTF_lADO...` (starts with PVTF)
- **Single-select field ID**: `PVTSSF_lADO...` (starts with PVTSSF)
- **Option ID**: Short hex string like `f75ad846` or `47fc9ee4`
- **Item ID** (used by scripts): `PVTI_...` (starts with PVTI)

---

## See Also

- Implementation plan: `/IMPLEMENTATION-PLAN-DIRECT-PROJECT-SYNC.md`
- Sintetic intermediate solution: `/SINTETIC-INTERMEDIATE-SOLUTION.md`
- GitHub Projects API docs: https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects
