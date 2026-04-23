#!/usr/bin/env python3
"""
Query all pull requests linked to a GitHub issue.

Shows PRs from all repositories that are linked to the issue.
This works for PRs created from branches made via gh issue develop.

Usage:
    ./gh-query-prs.py 7
    ./gh-query-prs.py 7 --verbose
"""

import argparse
import sys
from pathlib import Path

# Add script directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from gh_helpers import GitHubHelper
from config_loader import load_config


def main():
    parser = argparse.ArgumentParser(description="Query pull requests linked to an issue")
    parser.add_argument("issue", type=int, help="Issue number")
    parser.add_argument("--verbose", action="store_true", help="Show detailed PR information")

    args = parser.parse_args()

    # Load config
    config = load_config()
    github_repo = config["project"]["coordination_repo"]["github"]

    # Initialize
    gh = GitHubHelper(github_repo)

    issue_num = args.issue

    try:
        # Get issue details
        issue = gh.get_issue(issue_num)
        print(f"\nIssue #{issue_num}: {issue['title']}")
        print(f"URL: {issue['url']}\n")

        # Get linked PRs
        prs = gh.get_linked_prs(issue_num)

        if not prs:
            print("No pull requests linked to this issue.")
            print("\nNote: PRs are only automatically linked if they were created from")
            print("      branches made with: gh issue develop <issue> --branch-repo <repo>")
            return 0

        print(f"Linked pull requests ({len(prs)}):\n")

        for i, pr in enumerate(prs, 1):
            # PR references have repository and number fields
            repo_name = pr.get("repository", {}).get("name", "unknown")
            repo_owner = pr.get("repository", {}).get("owner", {}).get("login", "unknown")
            pr_number = pr.get("number", "?")
            pr_url = pr.get("url", "")

            full_repo = f"{repo_owner}/{repo_name}"

            print(f"{i}. PR #{pr_number} in {full_repo}")
            print(f"   {pr_url}")

            if args.verbose:
                # Get full PR details
                try:
                    gh_pr = GitHubHelper(full_repo)
                    result = gh_pr._run_gh([
                        "pr", "view", str(pr_number),
                        "--repo", full_repo,
                        "--json", "title,state,author,createdAt"
                    ])
                    import json
                    pr_details = json.loads(result.stdout)

                    print(f"   Title: {pr_details.get('title', 'N/A')}")
                    print(f"   State: {pr_details.get('state', 'N/A')}")
                    print(f"   Author: {pr_details.get('author', {}).get('login', 'N/A')}")
                    print(f"   Created: {pr_details.get('createdAt', 'N/A')}")
                except Exception as e:
                    print(f"   (Could not fetch details: {e})")

            print()

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
