#!/usr/bin/env python3
"""
Stop working on a GitHub issue and sync time tracking.

This script:
1. Ends the current time tracking session
2. Calculates session duration
3. Syncs total logged time to GitHub Project (if configured)
4. Displays time summary

Note: This does NOT release the agent or close the issue. Use:
- gh-release-agent.py to release your agent
- gh pr create to mark work as complete

Usage:
    ./gh-stop-work.py 7
    ./gh-stop-work.py 7 --no-sync  # Don't sync to GitHub
"""

import argparse
import sys
from pathlib import Path

# Add script directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from local_work import LocalWork
from gh_time_tracking import GitHubTimeTracking
from config_loader import load_config


def format_duration(minutes):
    """Format minutes into human-readable duration."""
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes / 60
    return f"{hours:.1f}h ({minutes}m)"


def main():
    parser = argparse.ArgumentParser(description="Stop working on a GitHub issue")
    parser.add_argument("issue", type=int, help="Issue number")
    parser.add_argument("--no-sync", action="store_true", help="Don't sync time to GitHub Project")

    args = parser.parse_args()

    # Load config
    config = load_config()
    project_name = config["project"]["name"]
    coord_repo = config["project"]["coordination_repo"]["github"]
    project_board_id = config["project"]["github"].get("project_board_id")

    # Support both new and old config formats
    project_fields = config["project"]["github"].get("project_fields", {})
    time_tracking_config = config["project"]["github"].get("time_tracking_fields", {})

    # Try new format first, fall back to old format
    logged_time_field_id = (
        project_fields.get("logged_time", {}).get("field_id") or
        time_tracking_config.get("logged_time_field_id")
    )

    # Initialize helpers
    coord_repo_root = Path(__file__).parent.parent.parent.parent
    local_work = LocalWork(coord_repo_root, project_name, coord_repo)

    issue_num = args.issue

    print(f"\n⏹️  Stopping work on issue #{issue_num}...\n")

    # Check if issue has active work
    issue_data = local_work.get_issue(str(issue_num))
    if not issue_data:
        print(f"❌ Error: No active work found for issue #{issue_num}", file=sys.stderr)
        print("   Start work first with: ./gh-start-task.py", file=sys.stderr)
        return 1

    # Step 1: Stop current session
    print("1. Ending current work session...")
    session_minutes = local_work.stop_work(str(issue_num))

    if session_minutes is None:
        print("   ⚠️  No active session found (already stopped?)")
        session_minutes = 0
    else:
        print(f"   ✓ Session ended: {format_duration(session_minutes)}")

    # Get total time
    issue_data = local_work.get_issue(str(issue_num))  # Refresh
    total_minutes = issue_data["time_tracking"]["total_minutes"]
    print(f"   Total logged time: {format_duration(total_minutes)}")

    # Step 2: Sync to GitHub Project (if configured and not disabled)
    if not args.no_sync and project_board_id and logged_time_field_id:
        github_project_item_id = issue_data.get("github_project_item_id")

        if github_project_item_id:
            print("2. Syncing time to GitHub Project...")
            try:
                time_tracker = GitHubTimeTracking(project_board_id, logged_time_field_id)
                total_hours = total_minutes / 60
                success = time_tracker.sync_logged_time(github_project_item_id, total_hours)

                if success:
                    print(f"   ✓ Synced {total_hours:.2f}h to GitHub Project 'Logged time' field")
                    local_work.update_github_sync(str(issue_num))
                else:
                    print(f"   ⚠️  Failed to sync to GitHub Project", file=sys.stderr)
            except Exception as e:
                print(f"   ⚠️  Error syncing to GitHub: {e}", file=sys.stderr)
        else:
            print("2. Skipping GitHub sync (issue not in project board)")
    elif args.no_sync:
        print("2. Skipping GitHub sync (--no-sync flag)")
    elif not project_board_id:
        print("2. Skipping GitHub sync (project_board_id not configured)")
    elif not logged_time_field_id:
        print("2. Skipping GitHub sync (logged_time_field_id not configured)")

    # Summary
    print(f"\n✅ Work session stopped!")
    print(f"   This session: {format_duration(session_minutes)}")
    print(f"   Total time: {format_duration(total_minutes)}")

    if issue_data.get("worktree"):
        print(f"\n   Resume work with: ./gh-start-task.py {issue_num} --agent {issue_data['agent_id']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
