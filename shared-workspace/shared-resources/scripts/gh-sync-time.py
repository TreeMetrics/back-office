#!/usr/bin/env python3
"""
Manually sync time tracking to GitHub Project.

Useful when:
- GitHub sync failed during gh-stop-work.py
- You want to manually update logged time
- Testing time tracking configuration

Usage:
    ./gh-sync-time.py 7                    # Sync from local-work.json
    ./gh-sync-time.py 7 --hours 5.5        # Manually specify hours
    ./gh-sync-time.py 7 --show             # Show current values without syncing
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
    parser = argparse.ArgumentParser(description="Sync time tracking to GitHub Project")
    parser.add_argument("issue", type=int, help="Issue number")
    parser.add_argument("--hours", type=float, help="Manually specify hours (instead of using local-work.json)")
    parser.add_argument("--show", action="store_true", help="Show current values without syncing")

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

    # Check configuration
    if not project_board_id:
        print("❌ Error: project_board_id not configured in project-shared.yaml", file=sys.stderr)
        return 1

    if not logged_time_field_id:
        print("❌ Error: logged_time_field_id not configured in project-shared.yaml", file=sys.stderr)
        print("   Get field ID with: gh project field-list <project-number> --owner <org>", file=sys.stderr)
        return 1

    # Initialize helpers
    coord_repo_root = Path(__file__).parent.parent.parent.parent
    local_work = LocalWork(coord_repo_root, project_name, coord_repo)
    time_tracker = GitHubTimeTracking(project_board_id, logged_time_field_id)

    issue_num = args.issue

    print(f"\n⏱️  Time tracking for issue #{issue_num}\n")

    # Get local data
    issue_data = local_work.get_issue(str(issue_num))

    if not issue_data and not args.hours:
        print(f"❌ Error: No local work data for issue #{issue_num}", file=sys.stderr)
        print("   Either start work first, or use --hours to manually specify time", file=sys.stderr)
        return 1

    # Determine hours to sync
    if args.hours:
        hours_to_sync = args.hours
        print(f"Using manually specified time: {hours_to_sync:.2f}h")
    elif issue_data:
        total_minutes = issue_data["time_tracking"]["total_minutes"]
        hours_to_sync = total_minutes / 60
        print(f"Local logged time: {format_duration(total_minutes)} ({hours_to_sync:.2f}h)")
    else:
        print("❌ Error: No time value available", file=sys.stderr)
        return 1

    # Get GitHub Project item ID
    github_project_item_id = None
    if issue_data:
        github_project_item_id = issue_data.get("github_project_item_id")

    if not github_project_item_id:
        print("Getting GitHub Project item ID...")
        github_project_item_id = time_tracker.get_project_item_id_for_issue(issue_num, coord_repo)

    if not github_project_item_id:
        print(f"❌ Error: Issue #{issue_num} not found in project board", file=sys.stderr)
        print("   Make sure the issue is added to the GitHub Project", file=sys.stderr)
        return 1

    print(f"GitHub Project item ID: {github_project_item_id}")

    # Show mode - just display current values
    if args.show:
        print("\nCurrent GitHub Project value:")
        github_hours = time_tracker.get_logged_time(github_project_item_id)
        if github_hours is not None:
            print(f"  Logged time: {github_hours:.2f}h")
        else:
            print(f"  Logged time: (not set)")

        print(f"\nLocal value: {hours_to_sync:.2f}h")

        if github_hours != hours_to_sync:
            print(f"\n⚠️  Values differ! Run without --show to sync local → GitHub")
        else:
            print(f"\n✓ Values match")

        return 0

    # Sync to GitHub
    print(f"\nSyncing {hours_to_sync:.2f}h to GitHub Project...")
    try:
        success = time_tracker.sync_logged_time(github_project_item_id, hours_to_sync)

        if success:
            print(f"✅ Successfully synced {hours_to_sync:.2f}h to 'Logged time' field")

            # Update local sync timestamp
            if issue_data:
                local_work.update_github_sync(str(issue_num))
                print(f"   Updated local sync timestamp")

            return 0
        else:
            print(f"❌ Failed to sync to GitHub Project", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"❌ Error syncing to GitHub: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
