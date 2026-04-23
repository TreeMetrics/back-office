#!/usr/bin/env python3
"""
Create a linked branch for a GitHub issue.

This script creates a branch linked to a GitHub issue using gh issue develop.
The branch will automatically link any PRs created from it to the issue.

Branch names follow the convention: {coord_project}_{issue#}_{description}
Example: qarlbo_16_baseline_activity

This prevents collisions when multiple coordination projects share code repos.

Usage:
    ./gh-create-branch.py 7 --repo tm_api -d "fix_auth_bug"
    ./gh-create-branch.py 7 --repo tm_api --worktree -d "baseline_activity"
    ./gh-create-branch.py 7 --repo TreeMetrics/tm_api --base master -d "feature_x"
    ./gh-create-branch.py 7 --repo tm_api  # Will prompt for description

Examples:
    # Create branch with description (no prompt)
    ./gh-create-branch.py 7 --repo tm_api -d "fix_auth_bug"

    # Create branch and worktree in one step
    ./gh-create-branch.py 7 --repo tm_api --worktree -d "baseline_activity"

    # Will prompt for description interactively
    ./gh-create-branch.py 7 --repo tm_api

    # Create branch but don't checkout (useful if working in different repo)
    ./gh-create-branch.py 7 --repo ember-forest --no-checkout -d "api_changes"
"""

import argparse
import sys
import subprocess
import re
from pathlib import Path
import yaml

# Add script directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from gh_helpers import GitHubHelper
from local_work import LocalWork
from config_loader import load_config, get_code_repo_config


def get_coord_repo_root():
    """Get coordination repository root."""
    return Path(__file__).parent.parent.parent.parent


def resolve_repo(repo_shortname, config):
    """
    Resolve repository shortname to full Org/repo format.

    Args:
        repo_shortname: Short name (e.g., "tm_api") or full name (e.g., "TreeMetrics/tm_api")
        config: Configuration dict

    Returns:
        tuple: (full_repo_name, default_branch)
    """
    # If already in Org/repo format, use as-is
    if "/" in repo_shortname:
        # Try to find default branch in config
        repo_config = get_code_repo_config(config, repo_shortname)
        if repo_config:
            return repo_shortname, repo_config.get("default_branch", "main")
        return repo_shortname, "main"

    # Look up in code_repositories by name
    try:
        repo_config = get_code_repo_config(config, repo_shortname)
        return repo_config["github"], repo_config.get("default_branch", "main")
    except KeyError:
        raise ValueError(f"Repository '{repo_shortname}' not found in project-shared.yaml code_repositories")


def get_worktree_path(repo_shortname, issue_num, config):
    """
    Get conventional worktree path for a repo and issue.

    Args:
        repo_shortname: Short name (e.g., "tm_api")
        issue_num: Issue number
        config: Configuration dict

    Returns:
        Path to worktree following convention: {worktree_parent}/{coord_project}_{issue}
    """
    # Look up worktree_parent for repo
    try:
        repo_config = get_code_repo_config(config, repo_shortname)
        if "worktree_parent" in repo_config:
            worktree_parent = Path(repo_config["worktree_parent"]).expanduser()
            # Get coordination project name (e.g., "hq-upgrades", "qarlbo")
            coord_project = config["project"]["coordination_repo"]["github"].split('/')[-1]
            # Convention: worktree at {worktree_parent}/{coord_project}_{issue}
            # e.g., ~/workspace/tm_api_dev/hq-upgrades_7
            worktree_path = worktree_parent / f"{coord_project}_{issue_num}"
            return str(worktree_path)
    except KeyError:
        pass

    # Fallback: ~/workspace/{repo}_{issue}
    return str(Path(f"~/workspace/{repo_shortname}_{issue_num}").expanduser())


def run_command(cmd, check=True):
    """Run a shell command and return result."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
    return result


def generate_branch_name(issue_num: int, description: str, config: dict) -> str:
    """
    Generate branch name following convention: {coord_project}_{issue#}_{description}

    Example: qarlbo_16_baseline_activity

    Args:
        issue_num: Issue number
        description: Short description for branch name
        config: Configuration dict

    Returns:
        Branch name following convention
    """
    coord_project = config["project"]["coordination_repo"]["github"].split('/')[-1]
    # Sanitize description: lowercase, replace spaces/special chars with underscore
    safe_desc = re.sub(r'[^a-z0-9]+', '_', description.lower()).strip('_')
    # Limit length to avoid overly long branch names
    if len(safe_desc) > 50:
        safe_desc = safe_desc[:50].rstrip('_')
    return f"{coord_project}_{issue_num}_{safe_desc}"


def get_primary_repo_path(repo_shortname: str, config: dict) -> str:
    """Get the local filesystem path for a code repository's primary clone."""
    shortname = repo_shortname.split('/')[-1] if '/' in repo_shortname else repo_shortname
    repo_config = get_code_repo_config(config, shortname)

    # Try local_path first (explicit path)
    local_path = repo_config.get("local_path")
    if local_path:
        return str(Path(local_path).expanduser())

    # Fall back to worktree_parent + primary_dir_name
    worktree_parent = repo_config.get("worktree_parent")
    primary_dir_name = repo_config.get("primary_dir_name")
    if worktree_parent and primary_dir_name:
        return str(Path(worktree_parent).expanduser() / primary_dir_name)

    raise ValueError(f"No local_path or worktree_parent/primary_dir_name configured for '{shortname}' in project-local.yaml")


def main():
    parser = argparse.ArgumentParser(
        description="Create a linked branch for a GitHub issue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create branch with description (no prompt)
  ./gh-create-branch.py 7 --repo tm_api -d "fix_auth_bug"
  # Creates: coordination-template-github-first_7_fix_auth_bug

  # Create branch and worktree at conventional path
  ./gh-create-branch.py 7 --repo tm_api --worktree -d "baseline_activity"

  # Will prompt for description interactively
  ./gh-create-branch.py 7 --repo tm_api

  # Create branch with custom worktree path
  ./gh-create-branch.py 7 --repo tm_api --worktree ~/custom/path -d "feature_x"

  # Create branch but don't checkout (useful for multi-repo workflows)
  ./gh-create-branch.py 7 --repo ember-forest --no-checkout -d "api_changes"

  # Use full repo name instead of shortname
  ./gh-create-branch.py 7 --repo TreeMetrics/tm_api --base master -d "feature_y"

Notes:
  - Branch names follow convention: {coord_project}_{issue#}_{description}
  - This prevents collisions when multiple projects share code repos
  - Branch will automatically link to issue via 'gh issue develop'
  - PRs created from this branch will appear in issue's Development panel
  - Multiple branches can be created for the same issue (multi-repo tasks)
        """
    )

    parser.add_argument("issue", type=int, help="Issue number")
    parser.add_argument("--repo", required=True, help="Repository shortname (tm_api, ember-forest) or full name (TreeMetrics/tm_api)")
    parser.add_argument("--description", "-d", help="Short description for branch name (e.g., 'baseline_activity'). If not provided, will prompt.")
    parser.add_argument("--base", help="Base branch (default: repo's default branch from config)")
    parser.add_argument("--worktree", nargs='?', const=True, help="Create worktree at conventional path, or specify custom path")
    parser.add_argument("--no-checkout", action="store_true", help="Don't checkout the new branch (only create it remotely)")

    args = parser.parse_args()

    # Load config
    try:
        config = load_config()
    except FileNotFoundError as e:
        print(f"❌ Error: Configuration file not found: {e}", file=sys.stderr)
        return 1

    project_name = config["project"]["name"]
    coordination_repo = config["project"]["coordination_repo"]["github"]

    # Resolve repository
    try:
        full_repo_name, default_branch = resolve_repo(args.repo, config)
        base_branch = args.base or default_branch
        print(f"📍 Target: {full_repo_name} (base: {base_branch})")
    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        print(f"\nAvailable repositories:", file=sys.stderr)
        for repo in config.get("code_repositories", []):
            print(f"  • {repo['name']} -> {repo['github']}", file=sys.stderr)
        return 1

    # Initialize helpers
    coord_repo_root = get_coord_repo_root()
    gh = GitHubHelper(coordination_repo)
    local_work = LocalWork(coord_repo_root, project_name, coordination_repo)

    issue_num = args.issue

    # Validate issue exists
    try:
        issue = gh.get_issue(issue_num)
        print(f"Issue #{issue_num}: {issue['title']}")
    except Exception as e:
        print(f"❌ Error: Could not find issue #{issue_num}: {e}", file=sys.stderr)
        return 1

    # Check if agent is assigned (warning only)
    issue_work = local_work.get_issue(str(issue_num))
    if not issue_work:
        print(f"⚠️  Warning: No local agent assigned to issue #{issue_num}", file=sys.stderr)
        print(f"   Consider running: ./gh-start-task.py {issue_num} --agent <agent-id>", file=sys.stderr)

    # Get or prompt for description to generate conventional branch name
    description = args.description
    if not description:
        # Show issue title as context
        print(f"\nBranch naming convention: {{coord_project}}_{{issue#}}_{{description}}")
        print(f"Example: coordination-template-github-first_{issue_num}_fix_auth_bug")
        description = input("\nEnter short description for branch (e.g., 'fix_auth_bug'): ").strip()
        if not description:
            print("❌ Error: Description is required for branch naming convention", file=sys.stderr)
            return 1

    # Generate conventional branch name
    branch_name = generate_branch_name(issue_num, description, config)
    print(f"\n   Branch name: {branch_name}")

    # Create linked branch
    print(f"\n1. Creating linked branch via gh issue develop...")
    try:
        # When using --worktree with a different repo, skip checkout
        # (gh issue develop --checkout corrupts config when run from different repo)
        checkout = not args.no_checkout and not args.worktree
        created_branch = gh.develop_issue(
            issue_num,
            branch_repo=full_repo_name,
            base=base_branch,
            checkout=checkout,
            name=branch_name
        )
        print(f"   ✓ Created branch: {created_branch}")
        if checkout:
            print(f"   ✓ Checked out locally")
    except Exception as e:
        print(f"   ❌ Error: {e}", file=sys.stderr)
        return 1

    # Create worktree if requested
    if args.worktree:
        print(f"\n2. Creating worktree...")

        # Determine worktree path
        if isinstance(args.worktree, str):
            # Custom path provided
            worktree_path = str(Path(args.worktree).expanduser().absolute())
        else:
            # Use conventional path
            repo_shortname = args.repo.split('/')[-1] if '/' in args.repo else args.repo
            worktree_path = get_worktree_path(repo_shortname, issue_num, config)

        print(f"   Path: {worktree_path}")

        # Get primary repo path - worktree must be created from target repo, not coordination repo
        repo_shortname = args.repo.split('/')[-1] if '/' in args.repo else args.repo
        try:
            primary_repo_path = get_primary_repo_path(repo_shortname, config)
        except ValueError as e:
            print(f"   ❌ Error: {e}", file=sys.stderr)
            print(f"   Branch was created successfully, but worktree requires local_path in config", file=sys.stderr)
            return 1

        try:
            # Fetch the branch from remote into the primary repo
            print(f"   Fetching branch from origin...")
            run_command(f'git -C "{primary_repo_path}" fetch origin {created_branch}', check=True)

            # Create worktree from primary repo (not coordination repo)
            result = run_command(f'git -C "{primary_repo_path}" worktree add "{worktree_path}" {created_branch}', check=True)
            print(f"   ✓ Worktree created")
            print(f"\n   Next: cd {worktree_path}")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error creating worktree: {e.stderr}", file=sys.stderr)
            print(f"   Branch was created successfully, but worktree failed", file=sys.stderr)
            return 1

    # Summary
    print(f"\n✅ Branch created and linked to issue #{issue_num}!")
    print(f"   Issue URL: {issue['url']}")
    print(f"   Branch: {created_branch}")
    print(f"   Repository: {full_repo_name}")

    print(f"\n   Next steps:")
    if args.worktree:
        print(f"   • cd {worktree_path}")
    print(f"   • Make your changes and commit")
    print(f"   • Create PR: ./gh-create-pr.py {issue_num} --title \"Your title\"")
    print(f"   • PR will automatically link to issue #{issue_num}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
