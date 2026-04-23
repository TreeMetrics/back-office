# Branch and Worktree Guidance for Agents

**Target audience:** Claude Code agents working in multi-agent coordination repositories

---

## Core Principle: Always Use Worktrees

**Default rule:** If your task involves code changes, **always create a worktree**.

```bash
# Standard workflow for code changes
./gh-start-task.py <issue#> --agent <agent-id>
./gh-create-branch.py <issue#> --repo Org/repo --worktree
```

**Why worktrees are standard:**
- You don't know if other agents are working (they might be)
- Prevents conflicts from branch switching
- Each task gets isolated workspace
- Safe for parallel multi-agent work
- No impact on main repository checkout

---

## When to Create a Branch/Worktree

### ✅ CREATE WORKTREE (Standard)

**Any task involving code changes:**
- Feature implementation
- Bug fixes
- Refactoring
- Code reviews (checking out PR branches)
- Any changes to tracked files in code repositories

**How:**
```bash
./gh-start-task.py <issue#> --agent <agent-id>
./gh-create-branch.py <issue#> --repo Org/repo --worktree

# Creates worktree at: ~/workspace/{repo}_dev/{project}_{issue#}/
# Example: ~/workspace/backend_dev/qarlbo_42/
```

### ❌ DON'T CREATE BRANCH/WORKTREE

**Tasks that don't touch code:**
- Documentation in coordination repo only
- Planning and design documents
- Research and investigation (no code output)
- Status updates and coordination

**How:**
```bash
# No --repo flag, work stays in coordination repo
./gh-start-task.py <issue#> --agent <agent-id>
```

---

## Exception: Working in Primary Repository

**Rule:** Only use the primary repository directory (not worktree) with **explicit developer permission** and **verification**.

### Valid Reasons

1. **Database migrations** (require primary database connection)
2. **Running test suite locally** (for debugging test failures)
3. **Database console access** (Rails console, psql with production config)

### Required Checks Before Using Primary Dir

**You MUST verify ALL of these:**

```markdown
1. ✅ Explicit permission from developer
   - Agent: "This requires working in the primary repository. Is that okay?"
   - Developer: "Yes, go ahead"

2. ✅ Clean git state
   - Check: git status shows "nothing to commit, working tree clean"
   - If not clean: STOP, ask developer to clean it first

3. ✅ No other agents working there
   - Check local state: ./gh-list-tasks.py
   - If another agent has a task without --worktree: STOP, coordinate with dev

4. ✅ Correct branch checked out
   - Check: git branch --show-current
   - Switch if needed: git checkout <correct-branch>
```

### Example: Database Migration Request

```
Agent: "This task requires running a database migration, which must be done
        in the primary repository directory (not a worktree) because migrations
        need access to the configured database connection.

        Can I work in ~/workspace/backend_dev (primary repo)?"

Developer: "Yes"

Agent: "Checking primary repository state..."
       [runs: cd ~/workspace/backend_dev && git status]
       "✓ Working tree clean"
       "✓ On branch main"
       "✓ No other agents working in primary dir"
       "Proceeding with migration..."
```

### Example: Permission Denied

```
Agent: "This task requires running tests locally in the primary repository.
        Can I work in ~/workspace/backend_dev (primary repo)?"

Developer: "No, the primary dir has uncommitted changes I'm testing"

Agent: "Understood. I'll work in a worktree instead for the code changes.
        Note: I won't be able to run the tests locally, but CI will run them
        when we create the PR."
```

---

## Multi-Repository Tasks

For tasks spanning multiple code repositories, create worktrees for each:

```bash
# Start task (no branches yet)
./gh-start-task.py 7 --agent myagent-multirepo

# Create branch + worktree in first repo
./gh-create-branch.py 7 --repo backend --worktree
# Creates: ~/workspace/backend_dev/project_7/

# Create branch + worktree in second repo
./gh-create-branch.py 7 --repo frontend --worktree
# Creates: ~/workspace/frontend_dev/project_7/

# Work in each worktree, create PRs
cd ~/workspace/backend_dev/project_7
# ... work ...
./gh-create-pr.py 7 --title "Backend: API changes"

cd ~/workspace/frontend_dev/project_7
# ... work ...
./gh-create-pr.py 7 --title "Frontend: UI changes"
```

Both PRs automatically link to issue #7.

---

## Worktree Restrictions

**Never do these in worktrees:**

❌ **Database migrations**
- Run in primary repository only
- Requires configured database connection
- Example: `rails db:migrate`

❌ **Running test suite**
- Tests may interact with shared database
- Tests may have race conditions
- Let CI handle test execution
- Exception: With explicit permission and verification, can run in primary dir

❌ **Database console operations**
- Rails console, psql, etc.
- Requires configured database connection
- Run in primary repository only

✅ **Do in worktrees:**
- All code changes
- Git commits and pushes
- Code review and inspection
- File editing and refactoring

---

## Worktree Conventions

### Naming

**Pattern:** `{worktree_parent}/{project}_{issue#}/`

**Examples:**
- `~/workspace/backend_dev/qarlbo_42/`
- `~/workspace/frontend_dev/qarlbo_42/`
- `~/workspace/tm_api_dev/sintetic_123/`

### Configuration

Set in `project-local.yaml` (per developer):

```yaml
code_repositories:
  - name: "backend"
    local_path: "~/workspace/backend_dev"
    worktree_parent: "~/workspace/backend_dev"

  - name: "frontend"
    local_path: "~/workspace/frontend_dev"
    worktree_parent: "~/workspace/frontend_dev"
```

**Convention:**
- `local_path`: Primary repository checkout
- `worktree_parent`: Directory where worktrees are created
- Often the same directory (worktrees created as subdirectories)

---

## Common Scenarios

### Scenario 1: Simple Feature Implementation

```bash
# 1. Start task
./gh-start-task.py 15 --agent alice-auth-feature

# 2. Create branch with worktree
./gh-create-branch.py 15 --repo backend --worktree

# 3. Work in worktree
cd ~/workspace/backend_dev/project_15
# ... implement feature ...
git add . && git commit -m "Add authentication" && git push

# 3. Create PR
./gh-create-pr.py 15 --title "Add JWT authentication"

# 4. Clean up
./gh-release-agent.py alice-auth-feature
```

**No interaction with primary repository needed.**

### Scenario 2: Feature + Migration

**⚠️ IMPORTANT:** Migrations must be run and schema.rb committed BEFORE creating the PR, otherwise CI will fail.

```bash
# 1. Start task
./gh-start-task.py 20 --agent bob-user-model

# 2. Create branch with worktree
./gh-create-branch.py 20 --repo backend --worktree

# 3. Work in worktree - create migration file
cd ~/workspace/backend_dev/project_20
rails generate migration AddUsersTable
# ... edit migration file ...
git add . && git commit -m "Add users migration" && git push

# 4. STOP - Ask user about running migration
Agent: "I've created a migration file. The migration must be run before
        creating the PR, otherwise CI will fail (schema.rb out of sync).

        Option A: You run it in the primary repo
        Option B: I can run it if you give me permission

        Which do you prefer?"

# Option A: User runs it
Developer: "I'll run it"
# User does: cd ~/workspace/backend_dev && git checkout <branch> && git pull && rails db:migrate
# User does: git add db/schema.rb && git commit -m "Run migration" && git push

# Option B: Agent runs it (with permission)
Developer: "Go ahead, primary dir is clean"

# 5. Run migration in primary dir
cd ~/workspace/backend_dev
git fetch origin
git checkout 20-add-users-table  # Branch name from gh issue develop
git pull origin 20-add-users-table
rails db:migrate

# 6. Commit and push schema.rb from primary dir
git add db/schema.rb
git commit -m "Run migration - update schema.rb"
git push

# 7. Return to worktree, pull changes, then create PR
cd ~/workspace/backend_dev/project_20
git pull  # Get the schema.rb changes
./gh-create-pr.py 20 --title "Add User model with migration"
```

**Key point:** The PR cannot be created until schema.rb reflects the migration. CI compares migration files against schema.rb and will fail if they're out of sync.

### Scenario 3: Documentation Only

```bash
# 1. Start task (no --repo, stays in coordination repo)
./gh-start-task.py 25 --agent charlie-api-docs

# 2. Work in coordination repo
cd ~/notes/project-coord/personal/project-25
# ... write documentation ...
git add . && git commit -m "Add API documentation" && git push

# 3. Update status (no PR needed for coordination-only work)
./gh-update-status.py 25 completed
./gh-release-agent.py charlie-api-docs
```

**No code repository involved.**

### Scenario 4: Debugging Test Failure

```bash
# 1. Start task
./gh-start-task.py 30 --agent debug-test

# 2. Create branch with worktree
./gh-create-branch.py 30 --repo backend --worktree

# 3. Implement fix in worktree
cd ~/workspace/backend_dev/project_30
# ... make changes ...
git add . && git commit -m "Fix user validation" && git push

# 4. Ask permission to run tests in primary dir
Agent: "I want to verify the fix by running tests locally.
        Can I use ~/workspace/backend_dev (primary dir) to run rspec?"

Developer: "Yes"

# 5. Run tests in primary dir
cd ~/workspace/backend_dev
git checkout project_30_fix-validation
git pull
rspec spec/models/user_spec.rb

# Tests pass!

# 6. Return to worktree for PR
cd ~/workspace/backend_dev/project_30
./gh-create-pr.py 30 --title "Fix user validation logic"
```

---

## Quick Decision Tree

```
Does task involve code changes?
├─ NO  → ./gh-start-task.py <issue#> --agent <id>
│         (No worktree, work in coordination repo)
│
└─ YES → ./gh-start-task.py <issue#> --agent <id>
          ./gh-create-branch.py <issue#> --repo <repo> --worktree
          (Always use worktree for code changes)

          Need to run migrations or tests locally?
          ├─ NO  → Stay in worktree (standard)
          │
          └─ YES → Ask permission to use primary dir
                   ├─ Permission granted + clean state
                   │  → Use primary dir temporarily
                   │
                   └─ Permission denied or not clean
                      → Stay in worktree, skip local test run
```

---

## Key Takeaways for Agents

1. **Default to worktrees** for any code changes
2. **Never assume** you can use the primary repository
3. **Always ask permission** before using primary dir
4. **Verify clean state** before using primary dir
5. **Let CI run tests** unless specifically debugging locally with permission
6. **Migrations require extra steps** - run in primary dir, commit schema.rb, THEN create PR
7. **Don't create PRs with uncommitted migrations** - CI will fail on schema.rb mismatch
8. **Don't worry about other agents** - worktrees isolate you automatically

---

## Reference: Command Comparison

| Scenario | Command |
|----------|---------|
| **Code changes (standard)** | `./gh-start-task.py 7 --agent name` then `./gh-create-branch.py 7 --repo backend --worktree` |
| **Coordination only** | `./gh-start-task.py 7 --agent name` |
| **Multi-repo** | Start task once, then multiple `./gh-create-branch.py 7 --repo <repo> --worktree` |
| **Check primary dir status** | `cd ~/workspace/backend_dev && git status` |
| **Check for other agents** | `./gh-list-tasks.py` |

---

## See Also

- **CLAUDE.md** - Complete agent instructions
- **GITHUB-FIRST-WORKFLOW.md** - Full workflow documentation
- **QUICK_REFERENCE.md** - Command cheat sheet
