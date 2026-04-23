#!/usr/bin/env python3
"""
Update GitHub issue status and project fields.

Updates the status label, dates, and estimates on a GitHub issue.

Usage:
    ./gh-update-status.py 7 in-progress              # Update status only
    ./gh-update-status.py 7 in-progress --target friday  # Status + target date
    ./gh-update-status.py 7 --start today --target friday  # Dates only (no status change)
    ./gh-update-status.py 7 --estimate 4             # Update estimate only
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
import re

# Add script directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from gh_helpers import GitHubHelper
from gh_time_tracking import GitHubProjectFields
from config_loader import load_config


def parse_date(date_str: str) -> str:
    """
    Parse date string to ISO format.

    Accepts:
        - YYYY-MM-DD (passthrough)
        - +Nd (N days from today)
        - +Nw (N weeks from today)
        - "today" (current date)
        - "friday", "monday" etc (next occurrence)

    Returns:
        ISO date string (YYYY-MM-DD)

    Raises:
        ValueError: If date format not recognized
    """
    # Handle "today" specially
    if date_str.lower() == 'today':
        return datetime.now().date().isoformat()

    # Already ISO format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str

    today = datetime.now().date()

    # Relative: +7d, +2w
    match = re.match(r'^\+(\d+)([dw])$', date_str.lower())
    if match:
        num, unit = int(match.group(1)), match.group(2)
        days = num if unit == 'd' else num * 7
        return (today + timedelta(days=days)).isoformat()

    # Day name: "friday", "monday"
    day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    if date_str.lower() in day_names:
        target = day_names.index(date_str.lower())
        current = today.weekday()
        delta = (target - current) % 7
        if delta == 0:
            delta = 7  # Next week if today
        return (today + timedelta(days=delta)).isoformat()

    raise ValueError(
        f"Cannot parse date: '{date_str}'\n"
        f"Valid formats: YYYY-MM-DD, today, +Nd (e.g., +7d), +Nw (e.g., +2w), "
        f"or day name (monday, tuesday, ...)"
    )


def main():
    # Load config first to get valid statuses
    config = load_config()
    valid_statuses = config["project"]["label_mappings"]["status"]

    parser = argparse.ArgumentParser(
        description="Update GitHub issue status and project fields",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update status only
  ./gh-update-status.py 7 in-progress

  # Update status and set target date
  ./gh-update-status.py 7 ready --target friday

  # Set dates without changing status
  ./gh-update-status.py 7 --start today --target "+5d"

  # Update estimate only
  ./gh-update-status.py 7 --estimate 4

  # Set all fields at once
  ./gh-update-status.py 7 in-progress --start today --target friday --estimate 8
        """
    )
    parser.add_argument("issue", type=int, help="Issue number")
    parser.add_argument("status", nargs='?', choices=valid_statuses,
                       help="New status (optional if updating other fields)")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD, today, +Nd, +Nw, or day name)")
    parser.add_argument("--target", help="Target date (YYYY-MM-DD, today, +Nd, +Nw, or day name)")
    parser.add_argument("--estimate", type=float, help="Estimated hours")

    args = parser.parse_args()

    # Validate at least one field to update
    if not args.status and not args.start and not args.target and args.estimate is None:
        parser.error("Must specify at least one of: status, --start, --target, or --estimate")

    # Initialize
    github_repo = config["project"]["coordination_repo"]["github"]
    gh = GitHubHelper(github_repo)

    issue_num = args.issue

    # Build description of what we're updating
    updates = []
    if args.status:
        updates.append(f"status → {args.status}")
    if args.start:
        updates.append(f"start → {args.start}")
    if args.target:
        updates.append(f"target → {args.target}")
    if args.estimate is not None:
        updates.append(f"estimate → {args.estimate}h")

    print(f"Updating issue #{issue_num}: {', '.join(updates)}")

    try:
        # Get current issue
        issue = gh.get_issue(issue_num)

        # Update status label if provided
        if args.status:
            current_labels = [l["name"] for l in issue.get("labels", [])]
            status_labels = [l for l in current_labels if l.startswith("status:")]

            gh.update_labels(
                issue_num,
                add=[f"status:{args.status}"],
                remove=status_labels if status_labels else None
            )
            print(f"   ✓ Label updated to 'status:{args.status}'")

        # Get project board config
        project_board_id = config["project"]["github"].get("project_board_id")
        project_fields = config["project"]["github"].get("project_fields", {})
        status_config = project_fields.get("status", {})
        status_field_id = status_config.get("field_id")
        status_options = status_config.get("options", {})
        planned_time_field_id = project_fields.get("planned_time", {}).get("field_id")
        target_date_field_id = project_fields.get("target_date", {}).get("field_id")
        start_date_field_id = project_fields.get("start_date", {}).get("field_id")

        # Update project fields if any are configured
        has_field_updates = (args.status or args.start or args.target or args.estimate is not None)
        has_field_config = project_board_id and (status_field_id or planned_time_field_id or
                                                  target_date_field_id or start_date_field_id)

        if has_field_updates and has_field_config:
            try:
                fields = GitHubProjectFields(
                    project_board_id,
                    status_field_id=status_field_id,
                    status_options=status_options,
                    planned_time_field_id=planned_time_field_id,
                    target_date_field_id=target_date_field_id,
                    start_date_field_id=start_date_field_id
                )

                item_id = fields.get_project_item_id_for_issue(issue_num, github_repo)
                if item_id:
                    # Update status field
                    if args.status and status_field_id and status_options:
                        if fields.update_status(item_id, args.status):
                            print(f"   ✓ Project status field updated to '{args.status}'")
                        else:
                            print("   ⚠️  Could not update project status field")

                    # Update start date
                    if args.start:
                        if not start_date_field_id:
                            print("   ⚠️  start_date field not configured, skipping --start")
                        else:
                            try:
                                parsed_date = parse_date(args.start)
                                if fields.update_start_date(item_id, parsed_date):
                                    print(f"   ✓ Start date set to {parsed_date}")
                                else:
                                    print("   ⚠️  Could not set start date")
                            except ValueError as e:
                                print(f"   ❌ {e}")

                    # Update target date
                    if args.target:
                        if not target_date_field_id:
                            print("   ⚠️  target_date field not configured, skipping --target")
                        else:
                            try:
                                parsed_date = parse_date(args.target)
                                if fields.update_target_date(item_id, parsed_date):
                                    print(f"   ✓ Target date set to {parsed_date}")
                                else:
                                    print("   ⚠️  Could not set target date")
                            except ValueError as e:
                                print(f"   ❌ {e}")

                    # Update estimate
                    if args.estimate is not None:
                        if not planned_time_field_id:
                            print("   ⚠️  planned_time field not configured, skipping --estimate")
                        elif fields.update_planned_time(item_id, args.estimate):
                            print(f"   ✓ Estimate set to {args.estimate}h")
                        else:
                            print("   ⚠️  Could not set estimate")

                else:
                    print("   ⚠️  Issue not in project board, skipping field updates")
            except Exception as e:
                print(f"   ⚠️  Project field update failed: {e}", file=sys.stderr)
        elif has_field_updates and not project_board_id:
            if args.start or args.target or args.estimate is not None:
                print("   ⚠️  Project board not configured, skipping field updates")

        print(f"\n✅ Issue #{issue_num} updated")
        print(f"   {issue['url']}")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
