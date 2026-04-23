#!/usr/bin/env python3
"""
List GitHub issues with local agent state.

Usage:
    ./gh-list-tasks.py                    # List all open issues
    ./gh-list-tasks.py --status planned   # Filter by status label
    ./gh-list-tasks.py --priority high    # Filter by priority label
    ./gh-list-tasks.py --assignee @me     # Filter by assignee
    ./gh-list-tasks.py --available        # Show only unassigned issues
"""

import argparse
import sys
from pathlib import Path

# Add script directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from local_work import LocalWork
from gh_helpers import GitHubHelper
from config_loader import load_config


def get_coord_repo_root():
    """Get coordination repository root."""
    return Path(__file__).parent.parent.parent.parent


def format_labels(labels):
    """Format label list, highlighting status/priority."""
    if not labels:
        return ""

    status = next((l["name"].replace("status:", "") for l in labels if l["name"].startswith("status:")), None)
    priority = next((l["name"].replace("priority:", "") for l in labels if l["name"].startswith("priority:")), None)
    types = [l["name"].replace("type:", "") for l in labels if l["name"].startswith("type:")]

    parts = []
    if status:
        parts.append(f"status:{status}")
    if priority:
        parts.append(f"pri:{priority}")
    if types:
        parts.append(f"type:{','.join(types)}")

    return " | ".join(parts)


def format_assignees(assignees):
    """Format assignee list."""
    if not assignees:
        return "unassigned"
    return ", ".join(a["login"] for a in assignees)


def main():
    parser = argparse.ArgumentParser(description="List GitHub issues with local agent state")
    parser.add_argument("--status", help="Filter by status label (e.g., planned, in-progress)")
    parser.add_argument("--priority", help="Filter by priority label (e.g., high, medium, low)")
    parser.add_argument("--assignee", help="Filter by assignee (@me or username)")
    parser.add_argument("--milestone", help="Filter by milestone name")
    parser.add_argument("--available", action="store_true", help="Show only unassigned issues")
    parser.add_argument("--state", default="open", choices=["open", "closed", "all"], help="Issue state")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of issues to show")

    args = parser.parse_args()

    # Load config
    config = load_config()
    project_name = config["project"]["name"]
    github_repo = config["project"]["coordination_repo"]["github"]

    # Initialize helpers
    coord_repo_root = get_coord_repo_root()
    gh = GitHubHelper(github_repo)
    local_work = LocalWork(coord_repo_root, project_name, github_repo)

    # Build label filters
    labels = []
    if args.status:
        labels.append(f"status:{args.status}")
    if args.priority:
        labels.append(f"priority:{args.priority}")

    # Query GitHub
    assignee = args.assignee
    if args.available:
        # Unfortunately gh CLI doesn't have --no-assignee, so we'll filter post-query
        assignee = None

    try:
        issues = gh.list_issues(
            labels=labels if labels else None,
            assignee=assignee,
            milestone=args.milestone,
            state=args.state,
            limit=args.limit
        )
    except Exception as e:
        print(f"Error querying GitHub: {e}", file=sys.stderr)
        return 1

    # Filter for available if requested
    if args.available:
        issues = [i for i in issues if not i.get("assignees")]

    # Get local agent assignments
    local_assignments = local_work.list_all_issues()

    # Display results
    if not issues:
        print("No issues found matching criteria.")
        return 0

    print(f"\n{'#':<6} {'Title':<40} {'Assignee':<20} {'Local Agent':<20} {'Labels':<30}")
    print("-" * 120)

    for issue in issues:
        num = issue["number"]
        title = issue["title"][:38] + ".." if len(issue["title"]) > 40 else issue["title"]
        assignee_str = format_assignees(issue.get("assignees", []))
        labels_str = format_labels(issue.get("labels", []))

        # Check local state
        local = local_assignments.get(str(num))
        local_agent = local["agent_id"] if local else "-"

        print(f"{num:<6} {title:<40} {assignee_str:<20} {local_agent:<20} {labels_str:<30}")

    print(f"\nTotal: {len(issues)} issue(s)")

    # Show summary of local agents
    active_agents = {}
    for issue_num, assignment in local_assignments.items():
        agent_id = assignment["agent_id"]
        if agent_id not in active_agents:
            active_agents[agent_id] = []
        active_agents[agent_id].append(issue_num)

    if active_agents:
        print(f"\nLocal agents active:")
        for agent_id, issue_nums in active_agents.items():
            print(f"  {agent_id}: issues {', '.join(issue_nums)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
