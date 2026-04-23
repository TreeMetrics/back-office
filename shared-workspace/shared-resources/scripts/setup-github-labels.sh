#!/bin/bash
# Setup GitHub Labels for TreeMetrics Coordination Repositories
#
# This script creates the TreeMetrics standard label set:
# - 9 status labels (triage → ready → in-progress → review → testing → done + blocked)
# - 3 priority labels (high, medium, low)
# - 5 type labels (feature, bug, infrastructure, docs, test)
#
# Usage:
#   ./setup-github-labels.sh <repo>
#
# Example:
#   ./setup-github-labels.sh TreeMetrics/hq-upgrades
#
# Prerequisites:
#   - gh CLI installed and authenticated
#   - Write access to target repository

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <org/repo>"
    echo "Example: $0 TreeMetrics/hq-upgrades"
    exit 1
fi

REPO="$1"

echo "========================================="
echo "GitHub Labels Setup (TreeMetrics Standard)"
echo "Repository: $REPO"
echo "========================================="
echo ""

# Check gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "ERROR: gh CLI not found. Install with: sudo apt install gh"
    exit 1
fi

# Check authentication
if ! gh auth status &> /dev/null; then
    echo "ERROR: Not authenticated with gh. Run: gh auth login"
    exit 1
fi

echo "Creating status labels (9)..."
echo ""

# Status labels (8-state workflow + blocked)
gh label create "status:triage" \
  --repo "$REPO" \
  --description "New issue, needs initial assessment" \
  --color "e1ecf4" \
  --force

gh label create "status:ready" \
  --repo "$REPO" \
  --description "Assessed and ready to start work" \
  --color "c5def5" \
  --force

gh label create "status:in-progress" \
  --repo "$REPO" \
  --description "Actively implementing" \
  --color "0e8a16" \
  --force

gh label create "status:ready-for-review" \
  --repo "$REPO" \
  --description "PR created, awaiting code review" \
  --color "d4c5f9" \
  --force

gh label create "status:review" \
  --repo "$REPO" \
  --description "Code review in progress" \
  --color "fbca04" \
  --force

gh label create "status:ready-to-test" \
  --repo "$REPO" \
  --description "PR merged, awaiting QA" \
  --color "0075ca" \
  --force

gh label create "status:testing" \
  --repo "$REPO" \
  --description "QA actively testing" \
  --color "5319e7" \
  --force

gh label create "status:blocked" \
  --repo "$REPO" \
  --description "Cannot proceed (external blocker)" \
  --color "d73a4a" \
  --force

gh label create "status:done" \
  --repo "$REPO" \
  --description "Released to production" \
  --color "6c757d" \
  --force

echo ""
echo "Creating priority labels (3)..."
echo ""

gh label create "priority:high" \
  --repo "$REPO" \
  --description "High priority" \
  --color "d93f0b" \
  --force

gh label create "priority:medium" \
  --repo "$REPO" \
  --description "Medium priority" \
  --color "fbca04" \
  --force

gh label create "priority:low" \
  --repo "$REPO" \
  --description "Low priority" \
  --color "0e8a16" \
  --force

echo ""
echo "Creating type labels (5)..."
echo ""

gh label create "type:feature" \
  --repo "$REPO" \
  --description "New feature or enhancement" \
  --color "a2eeef" \
  --force

gh label create "type:bug" \
  --repo "$REPO" \
  --description "Bug or defect" \
  --color "d73a4a" \
  --force

gh label create "type:infrastructure" \
  --repo "$REPO" \
  --description "Infrastructure or tooling work" \
  --color "fef2c0" \
  --force

gh label create "type:docs" \
  --repo "$REPO" \
  --description "Documentation" \
  --color "0075ca" \
  --force

gh label create "type:test" \
  --repo "$REPO" \
  --description "Testing or QA" \
  --color "b60205" \
  --force

echo ""
echo "✅ Labels created successfully!"
echo ""
echo "Verification:"
echo ""
echo "Status labels:"
gh label list --repo "$REPO" | grep "^status:" | sort
echo ""
echo "Priority labels:"
gh label list --repo "$REPO" | grep "^priority:" | sort
echo ""
echo "Type labels:"
gh label list --repo "$REPO" | grep "^type:" | sort

echo ""
echo "========================================="
echo "Setup complete!"
echo "========================================="
