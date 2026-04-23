#!/usr/bin/env python3
"""
Show PR review status for coordination issues or personal review queue.

Usage:
    ./gh-pr-status.py                          # PRs linked to coordination issues
    ./gh-pr-status.py --stale 3                # Only PRs with no activity in 3+ days
    ./gh-pr-status.py --reviewer @me --global  # All PRs awaiting my review
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from config_loader import load_config
from gh_helpers import GitHubHelper


def run_gh(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["gh"] + args, capture_output=True, text=True)


def get_pr_status(repo: str, pr_number: int) -> dict | None:
    """Get PR review status via gh pr view."""
    result = run_gh([
        "pr", "view", str(pr_number),
        "--repo", repo,
        "--json", "state,reviewDecision,updatedAt,title"
    ])
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def format_age(updated_at: str) -> str:
    """Format time since last update."""
    try:
        updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - updated
        if delta.days > 0:
            return f"{delta.days}d ago"
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours}h ago"
        return "now"
    except (ValueError, AttributeError):
        return "?"


def format_status(pr: dict) -> str:
    """Format review status as short string."""
    if pr.get("state") == "MERGED":
        return "Merged"
    if pr.get("state") == "CLOSED":
        return "Closed"
    decision = pr.get("reviewDecision")
    if decision == "APPROVED":
        return "Approved"
    if decision == "CHANGES_REQUESTED":
        return "Changes Requested"
    if decision == "REVIEW_REQUIRED":
        return "Awaiting Review"
    return "Open"


def get_stale_days(updated_at: str) -> int:
    """Get days since last update."""
    try:
        updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - updated).days
    except (ValueError, AttributeError):
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Show PR review status")
    parser.add_argument("--reviewer", metavar="USER", help="Filter by reviewer (e.g., @me)")
    parser.add_argument("--global", dest="global_mode", action="store_true",
                        help="Search all GitHub repos (requires --reviewer)")
    parser.add_argument("--stale", type=int, metavar="N", help="Only PRs inactive for N+ days")
    args = parser.parse_args()

    # Global mode: pass through to gh search
    if args.global_mode:
        if not args.reviewer:
            parser.error("--global requires --reviewer")
        cmd = ["gh", "search", "prs", f"--review-requested={args.reviewer}", "--state=open"]
        os.execvp("gh", cmd)

    # Default mode: PRs linked to coordination issues
    config = load_config()
    gh = GitHubHelper(config["project"]["coordination_repo"]["github"])

    print("Fetching PRs...", end="", flush=True)

    issues_with_prs = []
    for issue in gh.list_issues(state="open", limit=100):
        linked_prs = issue.get("closedByPullRequestsReferences", [])
        if linked_prs:
            issues_with_prs.append((issue, linked_prs))

    print("\r" + " " * 20 + "\r", end="")

    if not issues_with_prs:
        print("No open PRs linked to coordination issues.")
        return 0

    for issue, prs in issues_with_prs:
        issue_num = issue["number"]
        issue_title = issue["title"]

        pr_lines = []
        for pr_ref in prs:
            repo_info = pr_ref.get("repository", {})
            owner = repo_info.get("owner", {}).get("login", "")
            name = repo_info.get("name", "")
            pr_num = pr_ref.get("number")

            if not all([owner, name, pr_num]):
                continue

            repo = f"{owner}/{name}"
            pr = get_pr_status(repo, pr_num)

            if not pr or pr.get("state") != "OPEN":
                continue

            if args.stale and get_stale_days(pr.get("updatedAt", "")) < args.stale:
                continue

            pr_lines.append(f"  {name}#{pr_num:<6} {format_status(pr):<18} {format_age(pr.get('updatedAt', ''))}")

        if pr_lines:
            print(f"#{issue_num}: {issue_title}")
            for line in pr_lines:
                print(line)
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
