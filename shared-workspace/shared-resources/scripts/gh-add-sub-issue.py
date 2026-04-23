#!/usr/bin/env python3
"""
Add sub-issues to a parent issue using the GitHub sub-issues API.

This script properly links issues as sub-issues using the GitHub API,
rather than just adding text references in the issue body.

Usage:
    ./gh-add-sub-issue.py <parent> <child> [child2 ...]

Examples:
    # Add single sub-issue
    ./gh-add-sub-issue.py 24 63

    # Add multiple sub-issues at once
    ./gh-add-sub-issue.py 24 63 64 65

Notes:
    - All issue numbers refer to issues in the coordination repo (from config)
    - Uses the GitHub REST API: POST /repos/{owner}/{repo}/issues/{parent}/sub_issues
    - Requires the child issue's internal .id (fetched automatically)
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

# Add script directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from config_loader import load_config

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'


def run_gh(args: list, check: bool = True) -> subprocess.CompletedProcess:
    """Run a gh command."""
    cmd = ["gh"] + args
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def get_issue_id(repo: str, issue_num: int) -> Optional[int]:
    """
    Get the internal .id for an issue (not node_id, not issue number).

    Returns None if issue doesn't exist.
    """
    try:
        result = run_gh([
            "api", f"repos/{repo}/issues/{issue_num}",
            "--jq", ".id"
        ])
        return int(result.stdout.strip())
    except subprocess.CalledProcessError:
        return None


def issue_exists(repo: str, issue_num: int) -> bool:
    """Check if an issue exists."""
    result = run_gh([
        "api", f"repos/{repo}/issues/{issue_num}",
        "--jq", ".number"
    ], check=False)
    return result.returncode == 0


def add_sub_issue(repo: str, parent_num: int, child_id: int) -> Tuple[bool, str]:
    """
    Add a sub-issue to a parent issue.

    Args:
        repo: Repository in "owner/repo" format
        parent_num: Parent issue number
        child_id: Child issue's internal .id

    Returns:
        Tuple of (success: bool, message: str)
    """
    result = run_gh([
        "api", f"repos/{repo}/issues/{parent_num}/sub_issues",
        "-X", "POST",
        "-F", f"sub_issue_id={child_id}"
    ], check=False)

    if result.returncode == 0:
        return True, "linked successfully"
    else:
        # Try to extract error message
        error = result.stderr.strip()
        if "already" in error.lower():
            return False, "already a sub-issue"
        elif "not found" in error.lower():
            return False, "not found"
        else:
            return False, error or "unknown error"


def main():
    parser = argparse.ArgumentParser(
        description="Add sub-issues to a parent issue via GitHub API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add #63 as a sub-issue of #24
  ./gh-add-sub-issue.py 24 63

  # Add multiple sub-issues at once
  ./gh-add-sub-issue.py 24 63 64 65

Notes:
  - All issues are in the coordination repo (from project config)
  - This creates a proper parent-child relationship in GitHub
  - Different from just mentioning "#63" in the issue body
        """
    )

    parser.add_argument('parent', type=int, help='Parent issue number')
    parser.add_argument('children', type=int, nargs='+', help='Child issue number(s) to add as sub-issues')

    args = parser.parse_args()

    # Load config to get coordination repo
    config = load_config()
    repo = config["project"]["coordination_repo"]["github"]

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}Add Sub-Issues{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"\n{BLUE}Repository:{RESET} {CYAN}{repo}{RESET}")
    print(f"{BLUE}Parent issue:{RESET} #{args.parent}")
    print(f"{BLUE}Children:{RESET} {', '.join(f'#{c}' for c in args.children)}")

    # Validate parent exists
    print(f"\n{BLUE}Validating parent issue...{RESET}")
    if not issue_exists(repo, args.parent):
        print(f"{RED}✗ Parent issue #{args.parent} not found{RESET}")
        sys.exit(1)
    print(f"{GREEN}✓ Parent #{args.parent} exists{RESET}")

    # Process each child
    print(f"\n{BLUE}Linking sub-issues...{RESET}")
    results = []

    for child_num in args.children:
        # Get child's internal ID
        child_id = get_issue_id(repo, child_num)

        if child_id is None:
            results.append((child_num, False, "issue not found"))
            print(f"  {RED}✗ #{child_num}: issue not found{RESET}")
            continue

        # Add as sub-issue
        success, message = add_sub_issue(repo, args.parent, child_id)
        results.append((child_num, success, message))

        if success:
            print(f"  {GREEN}✓ #{child_num}: {message}{RESET}")
        else:
            print(f"  {RED}✗ #{child_num}: {message}{RESET}")

    # Summary
    succeeded = sum(1 for _, success, _ in results if success)
    failed = len(results) - succeeded

    print(f"\n{BOLD}{'='*60}{RESET}")
    if failed == 0:
        print(f"{GREEN}✓ All {succeeded} sub-issue(s) linked successfully{RESET}")
    elif succeeded == 0:
        print(f"{RED}✗ All {failed} sub-issue(s) failed{RESET}")
    else:
        print(f"{YELLOW}⚠ {succeeded} succeeded, {failed} failed{RESET}")

    print(f"\n{BLUE}View on GitHub:{RESET}")
    print(f"  https://github.com/{repo}/issues/{args.parent}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    # Exit with error if any failed
    sys.exit(1 if failed > 0 else 0)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Cancelled by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}✗ Unexpected error:{RESET} {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
