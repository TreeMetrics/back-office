# Testing the Coordination Scripts

This guide covers how to validate coordination scripts work correctly in your environment.

## Quick Validation

To verify scripts work with your configuration:

```bash
./tests/run-tests.sh
```

This creates a temporary test issue, verifies it appears in listings, and cleans up automatically.

## Testing Approaches

### Option A: Use [TEST] Prefix (Minimal Setup)

The simplest approach: create test issues in your existing coordination repo with a `[TEST]` prefix.

```bash
# Create test fixtures
./tests/create-test-fixtures.sh

# Test various workflows...

# Clean up when done
./tests/reset-test-env.sh
```

**Pros:** No additional repos needed, quick setup
**Cons:** Test data mixed with real issues (clearly marked with [TEST])

### Option B: Dedicated Test Environment (Comprehensive)

For thorough testing or CI, set up isolated test repositories.

#### 1. Create Test Repositories

```bash
# Option: Personal account
gh repo create my-coord-test --public
gh repo create my-code-test --public

# Option: Organization
gh repo create YourOrg/coord-test --template TreeMetrics/coordination-template-v2 --public
gh repo create YourOrg/code-test --public
```

#### 2. Configure Test Environment

```bash
# Copy template configs
cp tests/fixtures/project-shared-test.yaml /path/to/test-coord/project-shared.yaml
cp tests/fixtures/project-local-test.yaml.template /path/to/test-coord/project-local.yaml

# Edit both files with your test repo details
```

#### 3. Set Up Labels

```bash
cd /path/to/test-coord
./shared-workspace/shared-resources/scripts/setup-github-labels.sh YourOrg/coord-test
```

#### 4. Create Test Fixtures

```bash
./tests/create-test-fixtures.sh --repo YourOrg/coord-test
```

## Test Scripts

### create-test-fixtures.sh

Creates 6 test issues covering different states:

| Issue | Status | Purpose |
|-------|--------|---------|
| 1 | triage | New issue needing assessment |
| 2 | ready | Bug ready to start (high priority) |
| 3 | triage | For testing `gh-start-task.py` → in-progress |
| 4 | triage | For testing PR linking workflow |
| 5 | blocked | Blocked issue |
| 6 | done | Completed issue (closed) |

```bash
./tests/create-test-fixtures.sh                    # Uses config repo
./tests/create-test-fixtures.sh --repo Owner/Repo  # Specific repo
```

### reset-test-env.sh

Cleans up test data:

```bash
./tests/reset-test-env.sh          # Full: close [TEST] issues + clear local state
./tests/reset-test-env.sh --soft   # Soft: only clear local-work.json
```

### run-tests.sh

Quick validation that scripts execute correctly:

```bash
./tests/run-tests.sh
```

Creates a temporary issue, runs basic operations, cleans up automatically.

## Testing Specific Workflows

### Issue Lifecycle

```bash
# Create fixtures
./tests/create-test-fixtures.sh

# Find issue #3 (triage → in-progress test)
./shared-workspace/shared-resources/scripts/gh-list-tasks.py --status triage

# Start work (should transition to in-progress)
./shared-workspace/shared-resources/scripts/gh-start-task.py 3 --agent test-workflow

# Verify status changed
./shared-workspace/shared-resources/scripts/gh-list-tasks.py --status in-progress

# Clean up
./tests/reset-test-env.sh
```

### PR Linking (requires code repo)

```bash
# Start work on issue #4
./shared-workspace/shared-resources/scripts/gh-start-task.py 4 --agent test-pr

# Create branch with worktree
./shared-workspace/shared-resources/scripts/gh-create-branch.py 4 --repo code-test --worktree

# Go to worktree and make changes
cd ~/test/code-test_dev/coordination-test_4
echo "# Test" >> README.md
git add . && git commit -m "Test change"
git push -u origin HEAD

# Create PR (from worktree directory)
/path/to/coord/shared-workspace/shared-resources/scripts/gh-create-pr.py 4 --title "Test PR"

# Verify linking
/path/to/coord/shared-workspace/shared-resources/scripts/gh-query-prs.py 4
```

### Time Tracking (requires project board)

```bash
# Start task (begins time tracking)
./shared-workspace/shared-resources/scripts/gh-start-task.py 3 --agent test-time

# Work for a while...

# Stop work (syncs time to GitHub Project)
./shared-workspace/shared-resources/scripts/gh-stop-work.py 3

# Check synced time
./shared-workspace/shared-resources/scripts/gh-sync-time.py 3 --show
```

## Troubleshooting

### "gh CLI not found"

Install from https://cli.github.com/

### "Not authenticated with gh CLI"

```bash
gh auth login
```

### Scripts can't find config

Ensure you're running from the coordination repo root, or the script directory.

### Labels don't exist

Run the label setup script:
```bash
./shared-workspace/shared-resources/scripts/setup-github-labels.sh Owner/Repo
```

### Project board fields not configured

1. Create project board: `gh project create --owner Org --title "Board Name"`
2. Add required fields via GitHub UI or API
3. Get field IDs: `gh project field-list <num> --owner Org --format json`
4. Update `project-shared.yaml` with IDs

## CI Integration

For GitHub Actions, you'll need:

1. A dedicated test organization or repos
2. `GH_TOKEN` secret with repo access
3. Workflow that creates fixtures, runs tests, cleans up

See `tests/fixtures/` for example configurations.

```yaml
# Example .github/workflows/test.yml
name: Test Scripts
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install pyyaml
      - name: Run tests
        env:
          GH_TOKEN: ${{ secrets.TEST_REPO_TOKEN }}
        run: ./tests/run-tests.sh
```
