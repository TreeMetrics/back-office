#!/usr/bin/env python3
"""
Create a pull request from the current branch.

Must be run from a git repository (typically a worktree).
If the branch was created via gh-start-task.py, the PR will automatically link to the issue.

Verification (linting/formatting) is skipped by default since worktrees typically
lack the dependencies needed to run these checks. Use --verify to enable if your
environment supports it.

Usage:
    ./gh-create-pr.py 7 --title "Add user authentication"
    ./gh-create-pr.py 7 --title "Fix bug" --base master
    ./gh-create-pr.py 7 --title "Feature" --body "Detailed description"
    ./gh-create-pr.py 7 --title "Feature" --verify  # Run linting before PR
"""

import argparse
import sys
import subprocess
import shutil
from pathlib import Path

# Add script directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from gh_helpers import GitHubHelper
from gh_time_tracking import GitHubProjectFields
from config_loader import load_config


def detect_repo_type():
    """Detect repository type based on marker files."""
    cwd = Path.cwd()

    if (cwd / "Gemfile").exists():
        return "rails"
    elif (cwd / "package.json").exists():
        return "node"
    elif (cwd / "pyproject.toml").exists() or (cwd / "setup.py").exists():
        return "python"
    else:
        return None


def run_verification(repo_type):
    """
    Run verification commands based on repo type.
    Returns (success, message).
    """
    # Define verification commands per repo type
    # Each entry: (command_args, description, required_binary)
    verification_commands = {
        "rails": [
            (["bundle", "exec", "rubocop", "-a"], "Running rubocop...", "bundle"),
        ],
        "node": [
            (["npm", "run", "lint"], "Running npm lint...", "npm"),
        ],
        "python": [
            (["ruff", "check", ".", "--fix"], "Running ruff check...", "ruff"),
            (["ruff", "format", "."], "Running ruff format...", "ruff"),
        ],
    }

    if repo_type not in verification_commands:
        return True, f"No verification commands configured for repo type: {repo_type}"

    commands = verification_commands[repo_type]
    all_passed = True
    messages = []

    for cmd_args, description, required_binary in commands:
        # Check if binary exists
        if not shutil.which(required_binary):
            messages.append(f"  ⚠️  {required_binary} not found, skipping: {description}")
            continue

        print(f"  {description}")
        result = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )

        if result.returncode != 0:
            all_passed = False
            messages.append(f"  ❌ Failed: {' '.join(cmd_args)}")
            if result.stdout:
                messages.append(result.stdout)
            if result.stderr:
                messages.append(result.stderr)
        else:
            messages.append(f"  ✓ Passed: {description}")

    return all_passed, "\n".join(messages)


def get_current_branch():
    """Get the current git branch name."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()


def get_current_repo():
    """Get the current repository in Org/repo format."""
    # Try to get from git remote
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=False
    )

    if result.returncode == 0:
        url = result.stdout.strip()
        # Parse GitHub URL (https://github.com/Org/repo.git or git@github.com:Org/repo.git)
        if "github.com" in url:
            if url.endswith(".git"):
                url = url[:-4]
            if ":" in url:
                # SSH format
                return url.split(":")[-1]
            else:
                # HTTPS format
                return "/".join(url.split("/")[-2:])

    return None


def main():
    parser = argparse.ArgumentParser(description="Create a pull request")
    parser.add_argument("issue", type=int, help="Issue number")
    parser.add_argument("--title", required=True, help="PR title")
    parser.add_argument("--body", default="", help="PR description")
    parser.add_argument("--base", help="Base branch (default: repo default branch)")
    parser.add_argument("--draft", action="store_true", help="Create as draft PR")
    parser.add_argument("--verify", action="store_true",
                        help="Run pre-PR verification (linting/formatting)")

    args = parser.parse_args()

    # Load config
    config = load_config()
    coordination_repo = config["project"]["coordination_repo"]["github"]

    # Get current repository and branch
    try:
        current_branch = get_current_branch()
        current_repo = get_current_repo()

        if not current_repo:
            print("❌ Error: Could not detect current repository. Are you in a git repository?", file=sys.stderr)
            return 1

        print(f"Creating PR in {current_repo} from branch {current_branch}...")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error: Not in a git repository or no commits on branch", file=sys.stderr)
        return 1

    # Run verification only if --verify is specified
    if args.verify:
        repo_type = detect_repo_type()
        if repo_type:
            print(f"\n🔍 Running pre-PR verification ({repo_type} repo)...")
            success, message = run_verification(repo_type)
            print(message)

            if not success:
                print("\n❌ Verification failed. Fix issues and try again, or omit --verify to skip.")
                return 1
            else:
                print("✓ Verification passed\n")
        else:
            print("\n⚠️  Could not detect repo type, skipping verification")
            print("   (No Gemfile, package.json, or pyproject.toml found)\n")

    # Initialize GitHub helper for current repo
    gh_current = GitHubHelper(current_repo)

    # Get base branch
    if args.base:
        base_branch = args.base
    else:
        try:
            base_branch = gh_current.get_repo_default_branch()
            print(f"Using default base branch: {base_branch}")
        except Exception as e:
            print(f"⚠️  Could not detect default branch: {e}", file=sys.stderr)
            base_branch = "main"

    # Create PR
    print(f"Creating PR: {args.title}")
    try:
        # Add issue reference to body
        issue_url = f"https://github.com/{coordination_repo}/issues/{args.issue}"
        pr_body = f"{args.body}\n\nRelated to {issue_url}" if args.body else f"Related to {issue_url}"

        pr_url = gh_current.create_pr(
            title=args.title,
            body=pr_body,
            base=base_branch
        )

        print(f"\n✅ Pull request created!")
        print(f"   {pr_url}")
        print(f"\n   The PR will automatically link to issue #{args.issue}")
        print(f"   (if branch was created with gh-start-task.py)")

        # Update issue status to ready-for-review
        print(f"\nUpdating issue #{args.issue} status to 'ready-for-review'...")
        gh_coord = GitHubHelper(coordination_repo)

        # Update label
        try:
            issue = gh_coord.get_issue(args.issue)
            current_labels = [l["name"] for l in issue.get("labels", [])]
            status_labels = [l for l in current_labels if l.startswith("status:")]

            gh_coord.update_labels(
                args.issue,
                add=["status:ready-for-review"],
                remove=status_labels if status_labels else None
            )
            print("   ✓ Label updated to 'status:ready-for-review'")
        except Exception as e:
            print(f"   ⚠️  Could not update label: {e}", file=sys.stderr)

        # Also update project field if configured
        project_board_id = config["project"]["github"].get("project_board_id")
        project_fields = config["project"]["github"].get("project_fields", {})
        status_config = project_fields.get("status", {})
        status_field_id = status_config.get("field_id")
        status_options = status_config.get("options", {})

        field_configured = (project_board_id and status_field_id and status_options)

        if field_configured:
            try:
                fields = GitHubProjectFields(
                    project_board_id,
                    status_field_id=status_field_id,
                    status_options=status_options
                )

                item_id = fields.get_project_item_id_for_issue(args.issue, coordination_repo)
                if item_id:
                    success = fields.update_status(item_id, "ready-for-review")
                    if success:
                        print("   ✓ Project field updated to 'ready-for-review'")
                    else:
                        print("   ⚠️  Could not update project field")
                else:
                    print("   ⚠️  Issue not in project board, skipping field update")
            except Exception as e:
                print(f"   ⚠️  Project field update failed: {e}", file=sys.stderr)

        return 0

    except Exception as e:
        print(f"\n❌ Error creating PR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
