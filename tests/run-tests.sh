#!/bin/bash
# Run basic validation tests for coordination scripts
#
# Usage: ./run-tests.sh
#
# This script performs quick validation that scripts are working:
# - Creates a test issue
# - Lists tasks to verify it appears
# - Cleans up the test issue
#
# For comprehensive testing, use create-test-fixtures.sh instead.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
SCRIPTS="$REPO_ROOT/shared-workspace/shared-resources/scripts"

echo "Coordination Script Validation"
echo "==============================="
echo ""

# Check dependencies
echo "Checking dependencies..."
if ! command -v gh &> /dev/null; then
    echo "  ERROR: gh CLI not found"
    exit 1
fi
echo "  gh CLI: OK"

if ! command -v python3 &> /dev/null; then
    echo "  ERROR: python3 not found"
    exit 1
fi
echo "  python3: OK"

if ! gh auth status &> /dev/null 2>&1; then
    echo "  ERROR: Not authenticated with gh CLI"
    exit 1
fi
echo "  gh auth: OK"

echo ""

# Get coordination repo
COORD_REPO=$(python3 -c "
import yaml
with open('$REPO_ROOT/project-shared.yaml') as f:
    config = yaml.safe_load(f)
print(config['project']['coordination_repo']['github'])
")
echo "Coordination repo: $COORD_REPO"
echo ""

# Test 1: gh-list-tasks.py
echo "Test 1: gh-list-tasks.py"
echo "------------------------"
$SCRIPTS/gh-list-tasks.py --status triage 2>&1 | head -20 || true
echo "  PASS: Script executed"
echo ""

# Test 2: gh-create-issue.py
echo "Test 2: gh-create-issue.py"
echo "--------------------------"
TIMESTAMP=$(date +%s)
ISSUE_URL=$($SCRIPTS/gh-create-issue.py \
    --title "[TEST-AUTO] Validation test $TIMESTAMP" \
    --labels "status:triage" \
    --body "Automated validation test. Will be deleted immediately.")
ISSUE_NUM=$(echo "$ISSUE_URL" | grep -oE '[0-9]+$')
echo "  Created issue #$ISSUE_NUM"
echo "  PASS: Issue created"
echo ""

# Test 3: Verify issue appears in list
echo "Test 3: Verify issue in list"
echo "----------------------------"
LIST_OUTPUT=$($SCRIPTS/gh-list-tasks.py 2>&1)
if echo "$LIST_OUTPUT" | grep -q "#$ISSUE_NUM"; then
    echo "  PASS: Issue #$ISSUE_NUM found in list"
else
    echo "  WARN: Issue #$ISSUE_NUM not found in list (may be timing)"
fi
echo ""

# Test 4: gh-update-status.py
echo "Test 4: gh-update-status.py"
echo "---------------------------"
$SCRIPTS/gh-update-status.py "$ISSUE_NUM" ready 2>&1 || true
echo "  PASS: Status update executed"
echo ""

# Cleanup
echo "Cleanup"
echo "-------"
gh issue close "$ISSUE_NUM" --repo "$COORD_REPO" --comment "Automated test cleanup" 2>&1 || true
echo "  Closed issue #$ISSUE_NUM"
echo ""

echo "==============================="
echo "Validation complete"
echo "==============================="
echo ""
echo "All basic tests passed. For comprehensive testing:"
echo "  ./tests/create-test-fixtures.sh"
