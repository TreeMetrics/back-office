#!/bin/bash
# Reset test environment for coordination-template-v2
#
# Usage: ./reset-test-env.sh [--soft] [--repo OWNER/REPO]
#
# Options:
#   --soft         Only clear local state, keep GitHub issues
#   --repo         Override coordination repo (default: from config)
#
# Full reset (default): Closes all [TEST] issues and clears local state
# Soft reset: Only clears local-work.json, preserves GitHub issues

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Parse arguments
SOFT_RESET=false
COORD_REPO=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --soft)
            SOFT_RESET=true
            shift
            ;;
        --repo)
            COORD_REPO="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--soft] [--repo OWNER/REPO]"
            echo ""
            echo "Reset test environment for coordination scripts."
            echo ""
            echo "Options:"
            echo "  --soft             Only clear local state, keep GitHub issues"
            echo "  --repo OWNER/REPO  Override coordination repo (default: from config)"
            echo ""
            echo "Full reset (default):"
            echo "  - Closes all issues with [TEST] prefix"
            echo "  - Removes test agent entries from local-work.json"
            echo ""
            echo "Soft reset (--soft):"
            echo "  - Only removes test agent entries from local-work.json"
            echo "  - GitHub issues remain open"
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

echo "Test environment reset"
echo "======================"
echo "Coordination repo: $COORD_REPO"
echo "Mode: $(if $SOFT_RESET; then echo 'Soft (local only)'; else echo 'Full'; fi)"
echo ""

# Step 1: Clear test entries from local-work.json
LOCAL_WORK="$REPO_ROOT/local-work.json"
if [[ -f "$LOCAL_WORK" ]]; then
    echo "Cleaning local-work.json..."

    # Remove entries where agent_id starts with "test-" or issue title contains "[TEST]"
    python3 << EOF
import json
import sys

local_work_path = "$LOCAL_WORK"

try:
    with open(local_work_path, 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    print("  No local-work.json found")
    sys.exit(0)
except json.JSONDecodeError:
    print("  Invalid JSON in local-work.json, creating fresh file")
    data = {"active_work": {}}

original_count = len(data.get("active_work", {}))

# Filter out test entries
filtered_work = {}
for issue_num, entry in data.get("active_work", {}).items():
    agent_id = entry.get("agent_id", "")
    # Keep entries that don't look like test entries
    if not agent_id.startswith("test-") and not agent_id.startswith("test_"):
        filtered_work[issue_num] = entry

data["active_work"] = filtered_work
removed_count = original_count - len(filtered_work)

with open(local_work_path, 'w') as f:
    json.dump(data, f, indent=2)

print(f"  Removed {removed_count} test entries from local-work.json")
EOF
else
    echo "  No local-work.json found"
fi

# Step 2: Close GitHub issues (unless soft reset)
if ! $SOFT_RESET; then
    echo ""
    echo "Closing [TEST] issues on GitHub..."

    # Find all open issues with [TEST] in title
    TEST_ISSUES=$(gh issue list --repo "$COORD_REPO" --state open --search "[TEST] in:title" --json number --jq '.[].number' 2>/dev/null || echo "")

    if [[ -z "$TEST_ISSUES" ]]; then
        echo "  No open [TEST] issues found"
    else
        ISSUE_COUNT=$(echo "$TEST_ISSUES" | wc -l)
        echo "  Found $ISSUE_COUNT [TEST] issues to close"

        for num in $TEST_ISSUES; do
            echo "  Closing issue #$num..."
            gh issue close "$num" --repo "$COORD_REPO" --comment "Closed by test environment reset." 2>/dev/null || true
        done

        echo "  Closed $ISSUE_COUNT issues"
    fi
fi

echo ""
echo "========================================="
echo "Test environment reset complete"
echo "========================================="
echo ""

if $SOFT_RESET; then
    echo "Local state cleared. GitHub [TEST] issues preserved."
    echo ""
    echo "To also close GitHub issues, run without --soft flag."
else
    echo "All [TEST] issues closed and local state cleared."
    echo ""
    echo "To create fresh test fixtures:"
    echo "  ./tests/create-test-fixtures.sh"
fi
