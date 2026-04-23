#!/usr/bin/env python3
"""
Upgrade script for coordination repos.
Applies pending migrations after updating from coordination-template.

Run: python3 .claude/skills/upgrade/upgrade.py
"""

import json
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)


def expand_path(path: str) -> str:
    """Expand ~ to full home directory path."""
    return os.path.expanduser(path)


def load_yaml(path: Path) -> dict:
    """Load YAML file."""
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_json(path: Path) -> dict:
    """Load JSON file, return empty dict if doesn't exist."""
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def save_json(path: Path, data: dict):
    """Save JSON file with nice formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')


def get_repo_configs(repo_root: Path) -> list[dict]:
    """Extract repo configs from project-local.yaml.

    Returns list of dicts with 'worktree_parent' (expanded) and optional 'primary_dir_name'.
    """
    project_local = repo_root / "project-local.yaml"

    if not project_local.exists():
        return []

    config = load_yaml(project_local)
    repos = config.get("code_repositories") or config.get("project", {}).get("code_repositories", [])

    if not repos:
        return []

    results = []
    seen_parents = set()
    for repo in repos:
        if "worktree_parent" in repo:
            expanded = expand_path(repo["worktree_parent"])
            if expanded not in seen_parents:
                seen_parents.add(expanded)
                results.append({
                    "worktree_parent": expanded,
                    "primary_dir_name": repo.get("primary_dir_name"),
                })

    return results


def to_tilde_path(path: str) -> str:
    """Convert /home/user/... to ~/... for use in permission patterns."""
    home = os.path.expanduser("~")
    if path.startswith(home):
        return "~" + path[len(home):]
    return path


def migrate_additional_directories(repo_root: Path, repo_configs: list[dict]) -> bool:
    """
    Migration: Add worktree_parent paths to additionalDirectories.

    Adds paths to .claude/settings.local.json so agents can read files
    in worktree directories. (Read access only — Edit/Write handled separately.)

    Returns True if changes were made.
    """
    settings_local = repo_root / ".claude" / "settings.local.json"
    worktree_paths = [r["worktree_parent"] for r in repo_configs]

    # Load current settings
    settings = load_json(settings_local)

    if "permissions" not in settings:
        settings["permissions"] = {}

    current = set(settings["permissions"].get("additionalDirectories", []))
    needed = set(worktree_paths)

    if needed.issubset(current):
        print("  Already configured: additionalDirectories up to date")
        return False

    merged = sorted(current | needed)
    settings["permissions"]["additionalDirectories"] = merged
    save_json(settings_local, settings)

    added = needed - current
    print(f"  Added {len(added)} path(s) to additionalDirectories:")
    for p in sorted(added):
        print(f"    - {p}")

    return True


def migrate_edit_write_permissions(repo_root: Path, repo_configs: list[dict]) -> bool:
    """
    Migration: Add Edit/Write allow patterns for worktree directories,
    and deny patterns for primary checkout directories.

    - allow: Edit/Write on worktree_parent/** (covers all worktrees)
    - deny: Edit/Write on worktree_parent/primary_dir_name/** (protects primary checkout)

    Uses ~/path syntax (Claude Code expands ~ in permission patterns).

    Returns True if changes were made.
    """
    settings_local = repo_root / ".claude" / "settings.local.json"

    needed_allow = set()
    needed_deny = set()
    for repo in repo_configs:
        tilde = to_tilde_path(repo["worktree_parent"])
        needed_allow.add(f"Edit({tilde}/**)")
        needed_allow.add(f"Write({tilde}/**)")

        primary = repo.get("primary_dir_name")
        if primary:
            needed_deny.add(f"Edit({tilde}/{primary}/**)")
            needed_deny.add(f"Write({tilde}/{primary}/**)")

    # Load current settings
    settings = load_json(settings_local)

    if "permissions" not in settings:
        settings["permissions"] = {}

    current_allow = settings["permissions"].get("allow", [])
    current_deny = settings["permissions"].get("deny", [])

    allow_to_add = needed_allow - set(current_allow)
    deny_to_add = needed_deny - set(current_deny)

    if not allow_to_add and not deny_to_add:
        print("  Already configured: Edit/Write patterns up to date")
        return False

    if allow_to_add:
        settings["permissions"]["allow"] = current_allow + sorted(allow_to_add)
        print(f"  Added {len(allow_to_add)} allow pattern(s):")
        for p in sorted(allow_to_add):
            print(f"    + {p}")

    if deny_to_add:
        settings["permissions"]["deny"] = current_deny + sorted(deny_to_add)
        print(f"  Added {len(deny_to_add)} deny pattern(s) (primary checkout protection):")
        for p in sorted(deny_to_add):
            print(f"    - {p}")

    save_json(settings_local, settings)

    return True


def migrate_bash_script_permissions(repo_root: Path) -> bool:
    """
    Migration: Add Bash allow patterns with absolute paths for coordination scripts.

    The shared settings.json has Bash patterns with relative paths (./shared-workspace/...).
    These only match when the agent's CWD is the coordination repo root. When agents work
    in worktrees and call scripts via absolute paths (per Rule 6), the relative patterns
    don't match, causing permission prompts.

    Reads existing relative-path patterns from settings.json and creates absolute-path
    equivalents in settings.local.json.

    Returns True if changes were made.
    """
    settings_shared_path = repo_root / ".claude" / "settings.json"
    settings_local_path = repo_root / ".claude" / "settings.local.json"
    abs_prefix = str(repo_root)

    # Read shared settings to find relative-path Bash patterns
    shared = load_json(settings_shared_path)
    shared_allow = shared.get("permissions", {}).get("allow", [])

    needed_allow = set()
    for pattern in shared_allow:
        if not pattern.startswith("Bash("):
            continue

        abs_pattern = None
        if pattern.startswith("Bash(./"):
            abs_pattern = pattern.replace("Bash(./", f"Bash({abs_prefix}/", 1)
        elif pattern.startswith("Bash(python3 .claude/"):
            abs_pattern = pattern.replace(
                "Bash(python3 .claude/",
                f"Bash(python3 {abs_prefix}/.claude/",
                1,
            )
        elif pattern.startswith("Bash(python3 ./"):
            abs_pattern = pattern.replace(
                "Bash(python3 ./", f"Bash(python3 {abs_prefix}/", 1
            )
        # Patterns like "Bash(git add:*)" or "Bash(gh pr view:*)" are not path-based

        if abs_pattern:
            needed_allow.add(abs_pattern)

    if not needed_allow:
        print("  No relative-path Bash patterns found in settings.json")
        return False

    # Update settings.local.json
    settings = load_json(settings_local_path)
    if "permissions" not in settings:
        settings["permissions"] = {}

    current_allow = settings["permissions"].get("allow", [])
    allow_to_add = needed_allow - set(current_allow)

    if not allow_to_add:
        print("  Already configured: Bash script patterns up to date")
        return False

    settings["permissions"]["allow"] = current_allow + sorted(allow_to_add)
    save_json(settings_local_path, settings)

    print(f"  Added {len(allow_to_add)} allow pattern(s):")
    for p in sorted(allow_to_add):
        print(f"    + {p}")

    return True


def main():
    repo_root = Path.cwd()

    print("=== Coordination Repo Upgrade ===\n")

    # Check we're in a coordination repo
    if not (repo_root / "project-local.yaml").exists() and not (repo_root / "project-shared.yaml").exists():
        print("Error: Not in a coordination repo (no project-*.yaml found)")
        sys.exit(1)

    changes_made = False

    # Migration 3: Bash script permissions (absolute paths for worktrees)
    # Only needs the coordination repo path, not worktree configs
    print("Migration 3: Bash script permissions (absolute paths)")
    if migrate_bash_script_permissions(repo_root):
        changes_made = True

    print()

    # Extract repo configs (needed for migrations 1 and 2)
    repo_configs = get_repo_configs(repo_root)
    if not repo_configs:
        print("No worktree_parent paths in project-local.yaml.")
        if not (repo_root / "project-local.yaml").exists():
            print("Hint: Copy project-local.yaml.template to project-local.yaml and configure it.")
        if changes_made:
            print("\nUpgrade complete. Restart Claude Code for changes to take effect.")
        else:
            print("Nothing to do.")
        return

    # Migration 1: additionalDirectories (Read access for background agents)
    print("Migration 1: additionalDirectories (Read access)")
    if migrate_additional_directories(repo_root, repo_configs):
        changes_made = True

    print()

    # Migration 2: Edit/Write allow + deny patterns
    print("Migration 2: Edit/Write permissions (allow worktrees, deny primary)")
    if migrate_edit_write_permissions(repo_root, repo_configs):
        changes_made = True

    print()
    if changes_made:
        print("Upgrade complete. Restart Claude Code for changes to take effect.")
    else:
        print("No changes needed. Already up to date.")


if __name__ == "__main__":
    main()
