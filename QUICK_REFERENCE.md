# Quick Reference - Multi-Agent Coordination

**Bookmark this page for daily use.**

## 📍 Scripts Location
```
<repo-dir>/shared-workspace/shared-resources/scripts/
```

Tip: Add an alias to your shell:
```bash
alias coord='cd <repo-dir>/shared-workspace/shared-resources/scripts'
```

---

## 🚀 Essential Commands

### List Tasks
```bash
./gh-list-tasks.py                    # All open tasks
./gh-list-tasks.py --status planned   # Available tasks
./gh-list-tasks.py --priority high    # High priority
./gh-list-tasks.py --available        # Unassigned only
```

### Start Task
```bash
# Code changes (STANDARD - always use worktree)
./gh-start-task.py <issue#> --agent <your-name>
./gh-create-branch.py <issue#> --repo backend --worktree

# Coordination only (no code changes)
./gh-start-task.py <issue#> --agent <your-name>
```

**Default rule:** If task involves code, create a branch with worktree after starting. See BRANCH-AND-WORKTREE-GUIDANCE.md for details.

### Update Status
```bash
./gh-update-status.py <issue#> investigating
./gh-update-status.py <issue#> in-progress
./gh-update-status.py <issue#> blocked
./gh-update-status.py <issue#> ready-for-review
./gh-update-status.py <issue#> ready-to-test
./gh-update-status.py <issue#> completed
```

### Create PR
```bash
# Run from worktree directory
cd ~/workspace/repo_<issue#>
<repo-dir>/shared-workspace/shared-resources/scripts/gh-create-pr.py <issue#> --title "Your PR title"
```

### Query PRs
```bash
./gh-query-prs.py <issue#>              # List all PRs
./gh-query-prs.py <issue#> --verbose    # Detailed info
```

### Release Agent
```bash
./gh-release-agent.py <your-agent-name>
```

---

## 📋 Status Labels

| Label | Meaning |
|-------|---------|
| `status:planned` | Not started |
| `status:investigating` | Research/analysis |
| `status:in-progress` | Actively working |
| `status:blocked` | Can't proceed |
| `status:ready-for-review` | PR created |
| `status:ready-to-test` | Needs QA |
| `status:completed` | Done |

---

## 🔄 Typical Workflow

```bash
# 1. Find task
./gh-list-tasks.py --status planned

# 2. Start task
./gh-start-task.py 5 --agent myname

# 3. Create branch with worktree (for code changes)
./gh-create-branch.py 5 --repo backend --worktree

# 4. Do work
cd ~/workspace/backend_dev/project_5  # Your worktree location
# ... make changes ...
git add . && git commit -m "..." && git push

# 5. Create PR
./gh-create-pr.py 5 --title "Brief description"

# 6. Clean up
./gh-release-agent.py myname
```

**Time:** 2-5 commands per task

---

## 🌍 Multi-Repo Tasks

**Start task once, then create branches in each repo:**
```bash
# 1. Start task
./gh-start-task.py 7 --agent myname

# 2. Create branch in first repo
./gh-create-branch.py 7 --repo backend --worktree
cd ~/workspace/backend_dev/project_7
# ... work ...
<repo-dir>/shared-workspace/shared-resources/scripts/gh-create-pr.py 7 --title "Backend: ..."

# 3. Create branch in second repo
./gh-create-branch.py 7 --repo frontend --worktree
cd ~/workspace/frontend_dev/project_7
# ... work ...
<repo-dir>/shared-workspace/shared-resources/scripts/gh-create-pr.py 7 --title "Frontend: ..."
```

Both PRs link to issue #7 automatically!

---

## ⚠️ Common Mistakes

| ❌ Don't | ✅ Do |
|---------|-------|
| Edit GitHub issues manually | Use `./gh-update-status.py` |
| Use agent name "agent1" | Use descriptive: "auth-impl" |
| Forget to release agent | Always `./gh-release-agent.py` when done |
| Run gh-create-pr.py from wrong dir | Must be in worktree directory |
| Skip `--agent` parameter | Always provide unique agent name |

---

## 🆘 Quick Fixes

**"Agent already busy":**
```bash
./gh-release-agent.py <agent-name>
```

**"Branch already exists":**
```bash
git branch -D <branch-name>
git push origin --delete <branch-name>
```

**"Module not found: yaml":**
```bash
pip3 install pyyaml
```

**Check your local state:**
```bash
cat ~/.local/claude-coordination/<Project Name>/local-state.json | python3 -m json.tool
```

---

## 📚 More Help

- **Onboarding:** `<repo-dir>/ONBOARDING.md`
- **Full docs:** `<repo-dir>/shared-workspace/GITHUB-FIRST-WORKFLOW.md`
- **Issues:** Check your project's GitHub Issues page

---

**Print this page or keep it open while you work!**
