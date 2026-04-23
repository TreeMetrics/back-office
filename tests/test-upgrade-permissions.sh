#!/bin/bash
# Test the upgrade script's permission migrations
#
# Usage: ./tests/test-upgrade-permissions.sh
#
# Tests:
# 1. Fresh install: generates correct allow + deny patterns
# 2. Idempotent: running again makes no changes
# 3. Existing settings preserved: doesn't clobber existing allow/deny entries
# 4. Missing primary_dir_name: skips deny pattern (no error)
# 5. No project-local.yaml: exits gracefully
# 6. Bash script permissions: absolute-path patterns from settings.json

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
UPGRADE_SCRIPT="$REPO_ROOT/.claude/skills/apply-upgrade/upgrade.py"

PASS=0
FAIL=0
TOTAL=0

pass() {
    PASS=$((PASS + 1))
    TOTAL=$((TOTAL + 1))
    echo "  PASS: $1"
}

fail() {
    FAIL=$((FAIL + 1))
    TOTAL=$((TOTAL + 1))
    echo "  FAIL: $1"
}

assert_json_contains() {
    local file="$1" jq_expr="$2" expected="$3" desc="$4"
    local actual
    actual=$(python3 -c "
import json
with open('$file') as f:
    data = json.load(f)
result = $jq_expr
print(result)
")
    if [[ "$actual" == "$expected" ]]; then
        pass "$desc"
    else
        fail "$desc (expected: $expected, got: $actual)"
    fi
}

assert_json_list_contains() {
    local file="$1" jq_expr="$2" value="$3" desc="$4"
    local found
    found=$(python3 -c "
import json
with open('$file') as f:
    data = json.load(f)
items = $jq_expr
print('$value' in items)
")
    if [[ "$found" == "True" ]]; then
        pass "$desc"
    else
        fail "$desc (value '$value' not found)"
    fi
}

assert_json_list_not_contains() {
    local file="$1" jq_expr="$2" value="$3" desc="$4"
    local found
    found=$(python3 -c "
import json
with open('$file') as f:
    data = json.load(f)
items = $jq_expr
print('$value' in items)
")
    if [[ "$found" == "False" ]]; then
        pass "$desc"
    else
        fail "$desc (value '$value' should not be present)"
    fi
}

count_json_list() {
    local file="$1" jq_expr="$2"
    python3 -c "
import json
with open('$file') as f:
    data = json.load(f)
items = $jq_expr
print(len(items))
"
}

echo "Upgrade Script Permission Tests"
echo "================================"
echo ""

# Create temp directory for tests
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

HOME_DIR="$TMPDIR/fakehome"
mkdir -p "$HOME_DIR"

# ─────────────────────────────────────────────
echo "Test 1: Fresh install with two repos"
echo "-------------------------------------"

TEST1_DIR="$TMPDIR/test1"
mkdir -p "$TEST1_DIR/.claude"

cat > "$TEST1_DIR/project-shared.yaml" << 'EOF'
project:
  coordination_repo:
    github: "TestOrg/test-coord"
EOF

cat > "$TEST1_DIR/project-local.yaml" << EOF
project:
  coordination_repo:
    path: "$HOME_DIR/notes/test-project"

code_repositories:
  - name: "backend"
    worktree_parent: "$HOME_DIR/workspace/backend_dev"
    primary_dir_name: "backend"

  - name: "frontend"
    worktree_parent: "$HOME_DIR/workspace/frontend_dev"
    primary_dir_name: "frontend"
EOF

cd "$TEST1_DIR"
HOME="$HOME_DIR" python3 "$UPGRADE_SCRIPT" > /dev/null 2>&1

SETTINGS="$TEST1_DIR/.claude/settings.local.json"

# Check additionalDirectories
assert_json_list_contains "$SETTINGS" \
    "data['permissions']['additionalDirectories']" \
    "$HOME_DIR/workspace/backend_dev" \
    "additionalDirectories has backend_dev"

assert_json_list_contains "$SETTINGS" \
    "data['permissions']['additionalDirectories']" \
    "$HOME_DIR/workspace/frontend_dev" \
    "additionalDirectories has frontend_dev"

# Check allow patterns (should use ~ syntax)
assert_json_list_contains "$SETTINGS" \
    "data['permissions']['allow']" \
    "Edit(~/workspace/backend_dev/**)" \
    "allow has Edit for backend_dev"

assert_json_list_contains "$SETTINGS" \
    "data['permissions']['allow']" \
    "Write(~/workspace/frontend_dev/**)" \
    "allow has Write for frontend_dev"

# Check deny patterns (primary checkout protection)
assert_json_list_contains "$SETTINGS" \
    "data['permissions']['deny']" \
    "Edit(~/workspace/backend_dev/backend/**)" \
    "deny has Edit for backend primary"

assert_json_list_contains "$SETTINGS" \
    "data['permissions']['deny']" \
    "Write(~/workspace/frontend_dev/frontend/**)" \
    "deny has Write for frontend primary"

echo ""

# ─────────────────────────────────────────────
echo "Test 2: Idempotent (run again, no changes)"
echo "--------------------------------------------"

# Capture current state
BEFORE=$(cat "$SETTINGS")

cd "$TEST1_DIR"
OUTPUT=$(HOME="$HOME_DIR" python3 "$UPGRADE_SCRIPT" 2>&1)

AFTER=$(cat "$SETTINGS")

if [[ "$BEFORE" == "$AFTER" ]]; then
    pass "Settings file unchanged on second run"
else
    fail "Settings file changed on second run"
fi

if echo "$OUTPUT" | grep -q "Already configured"; then
    pass "Script reports already configured"
else
    fail "Script should report already configured"
fi

echo ""

# ─────────────────────────────────────────────
echo "Test 3: Preserves existing entries"
echo "-----------------------------------"

TEST3_DIR="$TMPDIR/test3"
mkdir -p "$TEST3_DIR/.claude"

cat > "$TEST3_DIR/project-shared.yaml" << 'EOF'
project:
  coordination_repo:
    github: "TestOrg/test-coord"
EOF

cat > "$TEST3_DIR/project-local.yaml" << EOF
code_repositories:
  - name: "api"
    worktree_parent: "$HOME_DIR/workspace/api_dev"
    primary_dir_name: "api"
EOF

# Pre-populate with existing entries
cat > "$TEST3_DIR/.claude/settings.local.json" << EOF
{
  "permissions": {
    "allow": [
      "Bash(git add:*)",
      "Bash(git commit:*)"
    ],
    "deny": [
      "Bash(rm -rf:*)"
    ],
    "additionalDirectories": [
      "/some/other/dir"
    ]
  }
}
EOF

cd "$TEST3_DIR"
HOME="$HOME_DIR" python3 "$UPGRADE_SCRIPT" > /dev/null 2>&1

SETTINGS3="$TEST3_DIR/.claude/settings.local.json"

# Existing entries preserved
assert_json_list_contains "$SETTINGS3" \
    "data['permissions']['allow']" \
    "Bash(git add:*)" \
    "Existing allow entry preserved"

assert_json_list_contains "$SETTINGS3" \
    "data['permissions']['deny']" \
    "Bash(rm -rf:*)" \
    "Existing deny entry preserved"

assert_json_list_contains "$SETTINGS3" \
    "data['permissions']['additionalDirectories']" \
    "/some/other/dir" \
    "Existing additionalDirectory preserved"

# New entries added
assert_json_list_contains "$SETTINGS3" \
    "data['permissions']['allow']" \
    "Edit(~/workspace/api_dev/**)" \
    "New Edit allow added alongside existing"

assert_json_list_contains "$SETTINGS3" \
    "data['permissions']['deny']" \
    "Edit(~/workspace/api_dev/api/**)" \
    "New Edit deny added alongside existing"

echo ""

# ─────────────────────────────────────────────
echo "Test 4: Missing primary_dir_name (no deny)"
echo "--------------------------------------------"

TEST4_DIR="$TMPDIR/test4"
mkdir -p "$TEST4_DIR/.claude"

cat > "$TEST4_DIR/project-shared.yaml" << 'EOF'
project:
  coordination_repo:
    github: "TestOrg/test-coord"
EOF

cat > "$TEST4_DIR/project-local.yaml" << EOF
code_repositories:
  - name: "scripts"
    worktree_parent: "$HOME_DIR/workspace/scripts_dev"
EOF

cd "$TEST4_DIR"
HOME="$HOME_DIR" python3 "$UPGRADE_SCRIPT" > /dev/null 2>&1

SETTINGS4="$TEST4_DIR/.claude/settings.local.json"

# Allow patterns still added
assert_json_list_contains "$SETTINGS4" \
    "data['permissions']['allow']" \
    "Edit(~/workspace/scripts_dev/**)" \
    "Edit allow added without primary_dir_name"

# No deny patterns (no primary to protect)
DENY_COUNT=$(count_json_list "$SETTINGS4" "data['permissions'].get('deny', [])")
if [[ "$DENY_COUNT" == "0" ]]; then
    pass "No deny patterns when primary_dir_name missing"
else
    fail "Should have 0 deny patterns, got $DENY_COUNT"
fi

echo ""

# ─────────────────────────────────────────────
echo "Test 5: No project-local.yaml"
echo "------------------------------"

TEST5_DIR="$TMPDIR/test5"
mkdir -p "$TEST5_DIR/.claude"

cat > "$TEST5_DIR/project-shared.yaml" << 'EOF'
project:
  coordination_repo:
    github: "TestOrg/test-coord"
EOF

cd "$TEST5_DIR"
OUTPUT5=$(HOME="$HOME_DIR" python3 "$UPGRADE_SCRIPT" 2>&1)

if echo "$OUTPUT5" | grep -q "Nothing to do"; then
    pass "Graceful exit without project-local.yaml"
else
    fail "Should report nothing to do"
fi

if [[ ! -f "$TEST5_DIR/.claude/settings.local.json" ]]; then
    pass "No settings.local.json created"
else
    fail "Should not create settings.local.json"
fi

echo ""

# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
echo "Test 6: Bash script permissions (absolute paths)"
echo "--------------------------------------------------"

TEST6_DIR="$TMPDIR/test6"
mkdir -p "$TEST6_DIR/.claude"

# Create a settings.json with relative Bash patterns (simulates shared settings)
cat > "$TEST6_DIR/.claude/settings.json" << 'EOF'
{
  "permissions": {
    "allow": [
      "Bash(./shared-workspace/shared-resources/scripts/gh-list-tasks.py:*)",
      "Bash(./shared-workspace/shared-resources/scripts/gh-create-pr.py:*)",
      "Bash(python3 .claude/skills/apply-upgrade/upgrade.py:*)",
      "Bash(git add:*)",
      "Bash(gh pr view:*)",
      "Bash(ls:*)"
    ]
  }
}
EOF

cat > "$TEST6_DIR/project-shared.yaml" << 'EOF'
project:
  coordination_repo:
    github: "TestOrg/test-coord"
EOF

cat > "$TEST6_DIR/project-local.yaml" << EOF
code_repositories:
  - name: "api"
    worktree_parent: "$HOME_DIR/workspace/api_dev"
    primary_dir_name: "api"
EOF

cd "$TEST6_DIR"
HOME="$HOME_DIR" python3 "$UPGRADE_SCRIPT" > /dev/null 2>&1

SETTINGS6="$TEST6_DIR/.claude/settings.local.json"

# Absolute-path Bash patterns were added
assert_json_list_contains "$SETTINGS6" \
    "data['permissions']['allow']" \
    "Bash($TEST6_DIR/shared-workspace/shared-resources/scripts/gh-list-tasks.py:*)" \
    "Absolute Bash pattern for gh-list-tasks.py"

assert_json_list_contains "$SETTINGS6" \
    "data['permissions']['allow']" \
    "Bash($TEST6_DIR/shared-workspace/shared-resources/scripts/gh-create-pr.py:*)" \
    "Absolute Bash pattern for gh-create-pr.py"

assert_json_list_contains "$SETTINGS6" \
    "data['permissions']['allow']" \
    "Bash(python3 $TEST6_DIR/.claude/skills/apply-upgrade/upgrade.py:*)" \
    "Absolute Bash pattern for upgrade.py"

# Non-path patterns should NOT get absolute equivalents
ALLOW_COUNT=$(count_json_list "$SETTINGS6" "data['permissions']['allow']")
# Expected: 3 absolute Bash + 2 Edit + 2 Write = 7 (from migrations 2+3)
# No absolute patterns for git/gh/ls commands
assert_json_list_not_contains "$SETTINGS6" \
    "data['permissions']['allow']" \
    "Bash($TEST6_DIR/git add:*)" \
    "git add not absolutized"

assert_json_list_not_contains "$SETTINGS6" \
    "data['permissions']['allow']" \
    "Bash($TEST6_DIR/gh pr view:*)" \
    "gh pr view not absolutized"

# Idempotent: run again, no new patterns
BEFORE6=$(cat "$SETTINGS6")
cd "$TEST6_DIR"
HOME="$HOME_DIR" python3 "$UPGRADE_SCRIPT" > /dev/null 2>&1
AFTER6=$(cat "$SETTINGS6")

if [[ "$BEFORE6" == "$AFTER6" ]]; then
    pass "Bash patterns idempotent on second run"
else
    fail "Bash patterns changed on second run"
fi

echo ""

# ─────────────────────────────────────────────
echo "================================"
echo "Results: $PASS passed, $FAIL failed (out of $TOTAL)"
echo "================================"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
