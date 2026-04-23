#!/bin/bash
# Create test fixtures for coordination-template-v2 testing
#
# Usage: ./create-test-fixtures.sh [--repo OWNER/REPO]
#
# Creates test issues in various states to validate coordination scripts.
# By default uses the coordination repo from project-shared.yaml.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
SCRIPTS="$REPO_ROOT/shared-workspace/shared-resources/scripts"

# Parse arguments
COORD_REPO=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --repo)
            COORD_REPO="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--repo OWNER/REPO]"
            echo ""
            echo "Creates test issues in various states for script validation."
            echo ""
            echo "Options:"
            echo "  --repo OWNER/REPO  Override coordination repo (default: from config)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Get coordination repo from config if not specified
if [[ -z "$COORD_REPO" ]]; then
    COORD_REPO=$(python3 -c "
import yaml
import sys
config_path = '$REPO_ROOT/project-shared.yaml'
try:
    with open(config_path) as f:
        config = yaml.safe_load(f)
    print(config['project']['coordination_repo']['github'])
except Exception as e:
    print(f'Error reading config: {e}', file=sys.stderr)
    sys.exit(1)
")
fi

echo "Creating test fixtures in: $COORD_REPO"
echo ""

# Check gh CLI is available
if ! command -v gh &> /dev/null; then
    echo "Error: gh CLI not found. Install from https://cli.github.com/"
    exit 1
fi

# Check authentication
if ! gh auth status &> /dev/null; then
    echo "Error: Not authenticated with gh CLI. Run: gh auth login"
    exit 1
fi

echo "Creating test issues..."
echo ""

# Issue 1: Triage state - new issue needing assessment
echo "1/6: Creating triage issue..."
gh issue create --repo "$COORD_REPO" \
    --title "[TEST] New feature request - needs triage" \
    --label "status:triage,priority:medium,type:feature" \
    --body "Test issue in triage state.

This issue simulates a new feature request that needs initial assessment.

**Expected workflow:**
1. Triage: assess scope and priority
2. Move to \`status:ready\` when assessed
3. Assign and start work

*Created by create-test-fixtures.sh*"

# Issue 2: Ready state with planning info
echo "2/6: Creating ready issue..."
gh issue create --repo "$COORD_REPO" \
    --title "[TEST] Bug fix ready to start" \
    --label "status:ready,priority:high,type:bug" \
    --body "Test issue in ready state with high priority.

This issue simulates a bug that has been triaged and is ready for work.

**Expected workflow:**
1. Assign to agent: \`gh-start-task.py <num> --agent test-agent\`
2. Create branch: \`gh-create-branch.py <num> --repo <code-repo>\`
3. Fix bug and create PR

*Created by create-test-fixtures.sh*"

# Issue 3: For testing in-progress workflow
echo "3/6: Creating issue for in-progress testing..."
gh issue create --repo "$COORD_REPO" \
    --title "[TEST] Feature for in-progress testing" \
    --label "status:triage,priority:medium,type:feature" \
    --body "Test issue to verify in-progress workflow.

**To test:**
\`\`\`bash
./gh-start-task.py <num> --agent test-inprogress-agent
./gh-list-tasks.py --status in-progress
\`\`\`

Should show this issue as in-progress with agent assigned.

*Created by create-test-fixtures.sh*"

# Issue 4: For testing PR linking
echo "4/6: Creating issue for PR linking test..."
gh issue create --repo "$COORD_REPO" \
    --title "[TEST] Work for PR linking test" \
    --label "status:triage,priority:low,type:infrastructure" \
    --body "Test issue to verify PR linking workflow.

**To test:**
1. Start task: \`gh-start-task.py <num> --agent test-pr-agent\`
2. Create branch: \`gh-create-branch.py <num> --repo <code-repo> --worktree\`
3. Make changes in worktree
4. Create PR: \`gh-create-pr.py <num> --title \"Test PR\"\`
5. Query PRs: \`gh-query-prs.py <num>\`

*Created by create-test-fixtures.sh*"

# Issue 5: Blocked state
echo "5/6: Creating blocked issue..."
gh issue create --repo "$COORD_REPO" \
    --title "[TEST] Blocked issue - external dependency" \
    --label "status:blocked,priority:high,type:feature" \
    --body "Test issue in blocked state.

**Blocked reason:** Waiting on external API documentation.

This simulates an issue that cannot proceed due to external factors.

**Expected workflow:**
1. When unblocked, update status: \`gh-update-status.py <num> in-progress\`
2. Continue normal workflow

*Created by create-test-fixtures.sh*"

# Issue 6: Done state (close it)
echo "6/6: Creating done issue..."
DONE_URL=$(gh issue create --repo "$COORD_REPO" \
    --title "[TEST] Completed documentation update" \
    --label "status:done,priority:medium,type:docs" \
    --body "Test issue in done state.

This simulates a completed issue for historical/reference testing.

*Created by create-test-fixtures.sh*")

# Extract issue number and close it
DONE_NUM=$(echo "$DONE_URL" | grep -oE '[0-9]+$')
gh issue close "$DONE_NUM" --repo "$COORD_REPO" --comment "Closed as part of test fixture setup."

echo ""
echo "========================================="
echo "Created 6 test issues in $COORD_REPO"
echo "========================================="
echo ""
echo "Next steps to test workflows:"
echo ""
echo "1. List all test issues:"
echo "   ./shared-workspace/shared-resources/scripts/gh-list-tasks.py"
echo ""
echo "2. Start work on an issue:"
echo "   ./shared-workspace/shared-resources/scripts/gh-start-task.py <num> --agent test-agent"
echo ""
echo "3. Clean up when done:"
echo "   ./tests/reset-test-env.sh"
echo ""
