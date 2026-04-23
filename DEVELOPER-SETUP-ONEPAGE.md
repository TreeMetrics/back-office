# Developer Setup - Existing Coordination Project

## Prerequisites (verify these first)
```bash
gh auth status       # GitHub CLI authenticated
python3 --version    # Python 3.7+
git --version        # Git installed
```

Missing something? → GitHub CLI: https://cli.github.com/

---

## Setup Steps (2-3 min)

**1. Clone the coordination repo**
```bash
git clone https://github.com/YourOrg/your-project-coordination
cd your-project-coordination
```

**2. Create your local config**
```bash
cp project-local.yaml.template project-local.yaml
```

Check `project-shared.yaml` to see which code repositories the project uses, then edit `project-local.yaml` with your local paths for each one:
```yaml
project:
  coordination_repo:
    path: "~/notes/your-project-coordination"

code_repositories:
  - name: "tm_api"  # Must match name in project-shared.yaml
    worktree_parent: "~/workspace/tm_api_dev"
    primary_dir_name: "tm_api"
```

**Note:** You may need to reorganize your code repo locations. The `worktree_parent` directory will contain both your primary checkout AND a worktree directory per issue:
```
~/workspace/tm_api_dev/
├── tm_api/            # Primary checkout (primary_dir_name)
├── myproject_7/       # Worktree for issue #7
└── myproject_12/      # Worktree for issue #12
```

**3. Install dependencies**
```bash
pip3 install -r shared-workspace/shared-resources/scripts/requirements.txt
# If pip3 not found: python3 -m pip install -r ...
```

**4. Start Claude Code and verify**
```bash
claude
```
Ask Claude:
- "List available tasks" — verifies GitHub connection
- "Verify my code repository paths are configured correctly" — verifies local config

✅ **Done!**

---

## Working with Claude

Claude reads `.claude/CLAUDE.md` and knows the workflow.

**Example prompts:**
- "List available tasks"
- "Start task #5 for me"
- "Create a branch for issue #5 in the tm_api repo"
- "I'm done with task #5, create a PR"
- "Release my agent"

---

## Troubleshooting
| Error | Fix |
|-------|-----|
| `gh: not logged in` | `gh auth login` |
| `ModuleNotFoundError: yaml` | `pip3 install pyyaml` |
| Agent already busy | Ask Claude to release the agent |
| Code repo path not found | Check `project-local.yaml` paths match your filesystem |

---

**Full docs:** `cat ONBOARDING.md` or `cat shared-workspace/GITHUB-FIRST-WORKFLOW.md`
