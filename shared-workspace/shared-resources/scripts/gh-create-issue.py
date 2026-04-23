#!/usr/bin/env python3
"""
Create a GitHub issue and automatically add to project board.

This script creates a GitHub issue and, if project_board_id is configured,
automatically adds it to the GitHub project board.

Usage:
    ./gh-create-issue.py --title "Issue title" [options]

Examples:
    # Create issue with status and priority labels
    ./gh-create-issue.py --title "Add health check script" --labels status:planned,priority:high

    # Create issue with description
    ./gh-create-issue.py --title "Fix diameter units bug" --body "The diameter field is using cm instead of mm"

    # Create issue and assign to yourself
    ./gh-create-issue.py --title "Feature request" --assignee @me

    # Create issue in specific repo (e.g., code repository)
    ./gh-create-issue.py --title "Bug fix" --repo TreeMetrics/tm_api

    # Skip project board (even if configured)
    ./gh-create-issue.py --title "Test" --no-project-board

Options:
    --title TEXT         Issue title (required)
    --body TEXT          Issue body/description (optional)
    --labels TEXT        Comma-separated labels (e.g., "status:planned,priority:high,type:bug")
    --assignee TEXT      Assign to user (@me for current user)
    --repo TEXT          GitHub repo in format org/repo (default: coordination repo)
    --no-project-board   Skip adding to project board even if configured
"""

import argparse
import sys
from pathlib import Path

# Add script directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from gh_helpers import GitHubHelper
from gh_time_tracking import GitHubProjectFields
from config_loader import load_config

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'


def parse_target_date(date_str: str) -> str:
    """
    Parse target date string to ISO format.

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
    from datetime import datetime, timedelta
    import re

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
        f"Valid formats: YYYY-MM-DD, +Nd (e.g., +7d), +Nw (e.g., +2w), "
        f"or day name (monday, tuesday, ...)"
    )


def create_issue_with_board_sync(
    title: str,
    body: str = "",
    labels: str = "",
    assignee: str = None,
    repo: str = None,
    skip_board: bool = False,
    estimate: float = None,
    milestone: str = None,
    target_date: str = None,
    start_date: str = None
):
    """
    Create a GitHub issue and add to project board if configured.

    Args:
        title: Issue title
        body: Issue description
        labels: Comma-separated labels
        assignee: Username to assign
        repo: Target repository (default: coordination repo)
        skip_board: Skip project board addition even if configured
        estimate: Estimated hours (sets Planned time field)
        milestone: Milestone name to add issue to
        target_date: Target date string (parsed by parse_target_date)
        start_date: Start date string (parsed by parse_target_date)
    """
    config = load_config()

    # Determine target repo
    if repo is None:
        repo = config["project"]["coordination_repo"]["github"]
        repo_type = "coordination"
    else:
        repo_type = "code"

    # Initialize GitHub helper
    gh = GitHubHelper(repo)

    # Parse labels
    label_list = [l.strip() for l in labels.split(",")] if labels else None

    # Create the issue
    print(f"\n{BLUE}📝 Creating GitHub Issue{RESET}")
    print(f"   Repository: {CYAN}{repo}{RESET} ({repo_type})")
    print(f"   Title: {title}")
    if body:
        preview = body[:100] + "..." if len(body) > 100 else body
        print(f"   Body: {preview}")
    if label_list:
        print(f"   Labels: {', '.join(label_list)}")
    if assignee:
        print(f"   Assignee: {assignee}")
    if milestone:
        print(f"   Milestone: {milestone}")
    if estimate:
        print(f"   Estimate: {estimate}h")
    if start_date:
        print(f"   Start: {start_date}")
    if target_date:
        print(f"   Target: {target_date}")

    try:
        issue = gh.create_issue(
            title=title,
            body=body,
            labels=label_list,
            assignee=assignee,
            milestone=milestone
        )
        print(f"{GREEN}✓ Issue created:{RESET} {issue['url']}")
        print(f"   Issue #{issue['number']}: {issue['title']}")

    except Exception as e:
        print(f"\n{RED}✗ Failed to create issue{RESET}")
        print(f"{RED}Error:{RESET} {e}")
        print(f"\n{YELLOW}Possible causes:{RESET}")
        print(f"  • gh CLI not authenticated (run: gh auth login)")
        print(f"  • No permission to create issues in {repo}")
        print(f"  • Repository {repo} doesn't exist")
        sys.exit(1)

    # Add to project board if configured
    if not skip_board:
        project_board_number = config["project"].get("github", {}).get("project_board_number")
        project_board_id = config["project"].get("github", {}).get("project_board_id")
        github_org = config["project"].get("github", {}).get("org")

        if project_board_number is None:
            print(f"\n{YELLOW}ℹ{RESET}  Project board not configured (project_board_number is null)")
            print(f"   Skipping project board addition")
            print(f"   To enable: Set project_board_number in project-shared.yaml")
        elif not github_org:
            print(f"\n{YELLOW}⚠{RESET}  GitHub org not configured, skipping project board addition")
        else:
            print(f"\n{BLUE}📋 Adding to Project Board{RESET}")
            print(f"   Project Board: #{CYAN}{project_board_number}{RESET}")
            print(f"   Organization: {github_org}")

            success = gh.add_issue_to_project(
                issue_url=issue['url'],
                project_id=project_board_number,
                org=github_org
            )

            if success:
                print(f"{GREEN}✓ Added to project board{RESET}")

                # Set Status field to 'triage' if configured
                project_fields = config["project"]["github"].get("project_fields", {})
                status_config = project_fields.get("status", {})
                status_field_id = status_config.get("field_id")
                status_options = status_config.get("options", {})

                # Get all field IDs from config
                planned_time_field_id = project_fields.get("planned_time", {}).get("field_id")
                target_date_field_id = project_fields.get("target_date", {}).get("field_id")
                start_date_field_id = project_fields.get("start_date", {}).get("field_id")

                # Set up GitHubProjectFields with all configured fields
                if status_field_id or planned_time_field_id or target_date_field_id or start_date_field_id:
                    try:
                        fields = GitHubProjectFields(
                            project_board_id,
                            planned_time_field_id=planned_time_field_id,
                            target_date_field_id=target_date_field_id,
                            start_date_field_id=start_date_field_id,
                            status_field_id=status_field_id,
                            status_options=status_options
                        )
                        item_id = fields.get_project_item_id_for_issue(issue['number'], repo)

                        if item_id:
                            # Set status to triage
                            if status_field_id and status_options and "triage" in status_options:
                                if fields.update_status(item_id, "triage"):
                                    print(f"{GREEN}✓ Status field set to 'triage'{RESET}")
                                else:
                                    print(f"{YELLOW}⚠{RESET}  Could not set status field")

                            # Set estimate if provided
                            if estimate:
                                if not planned_time_field_id:
                                    print(f"{YELLOW}⚠{RESET}  planned_time field not configured, skipping --estimate")
                                elif fields.update_planned_time(item_id, estimate):
                                    print(f"{GREEN}✓ Estimate set to {estimate}h{RESET}")
                                else:
                                    print(f"{YELLOW}⚠{RESET}  Could not set estimate")

                            # Set start date if provided
                            if start_date:
                                if not start_date_field_id:
                                    print(f"{YELLOW}⚠{RESET}  start_date field not configured, skipping --start")
                                else:
                                    try:
                                        parsed_date = parse_target_date(start_date)
                                        if fields.update_start_date(item_id, parsed_date):
                                            print(f"{GREEN}✓ Start date set to {parsed_date}{RESET}")
                                        else:
                                            print(f"{YELLOW}⚠{RESET}  Could not set start date")
                                    except ValueError as e:
                                        print(f"{RED}Error: {e}{RESET}")

                            # Set target date if provided
                            if target_date:
                                if not target_date_field_id:
                                    print(f"{YELLOW}⚠{RESET}  target_date field not configured, skipping --target")
                                else:
                                    try:
                                        parsed_date = parse_target_date(target_date)
                                        if fields.update_target_date(item_id, parsed_date):
                                            print(f"{GREEN}✓ Target date set to {parsed_date}{RESET}")
                                        else:
                                            print(f"{YELLOW}⚠{RESET}  Could not set target date")
                                    except ValueError as e:
                                        print(f"{RED}Error: {e}{RESET}")

                    except Exception as e:
                        print(f"{YELLOW}⚠{RESET}  Could not set project fields: {e}")
            else:
                # Non-fatal: issue was created, just couldn't add to board
                print(f"\n{YELLOW}⚠{RESET}  Could not add to project board (issue still created)")
                print(f"{YELLOW}Possible causes:{RESET}")
                print(f"  • Project board #{project_board_number} doesn't exist")
                print(f"  • No permission to modify project board")
                print(f"  • gh CLI not authenticated with project permissions")
                print(f"\n{YELLOW}Manual fix:{RESET}")
                print(f"  gh project item-add {project_board_number} --owner {github_org} --url {issue['url']}")
    else:
        print(f"\n{YELLOW}ℹ{RESET}  Skipping project board (--no-project-board flag)")

    # Summary
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{GREEN}✓ Complete!{RESET}")
    print(f"\n{BOLD}Issue URL:{RESET} {issue['url']}")
    print(f"{BOLD}Issue Number:{RESET} #{issue['number']}")
    print(f"\n{YELLOW}Next steps:{RESET}")
    print(f"  • View issue on GitHub: {issue['url']}")
    print(f"  • Start work: ./gh-start-task.py {issue['number']} --agent <your-agent-id>")
    print(f"{BOLD}{'='*70}{RESET}\n")

    return issue


def main():
    parser = argparse.ArgumentParser(
        description="Create GitHub issue and automatically add to project board",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create issue with labels
  ./gh-create-issue.py --title "Add health check script" \\
    --labels "status:triage,priority:high,type:feature"

  # Create issue with full description
  ./gh-create-issue.py --title "Fix diameter units bug" \\
    --body "The diameter field is using cm instead of mm" \\
    --labels "status:triage,priority:high,type:bug"

  # Create and assign to yourself
  ./gh-create-issue.py --title "New feature" --assignee @me

  # Create issue in code repo (not coordination repo)
  ./gh-create-issue.py --title "Fix API endpoint" --repo TreeMetrics/tm_api

  # Skip project board
  ./gh-create-issue.py --title "Test" --no-project-board

Notes:
  - If project_board_id is configured, issue is automatically added to board
  - If project_board_id is null, skips board addition (no error)
  - Issue creation succeeds even if board addition fails
        """
    )

    parser.add_argument('--title', required=True, help='Issue title')
    parser.add_argument('--body', default="", help='Issue body/description')
    parser.add_argument('--labels', default="", help='Comma-separated labels (e.g., "status:triage,priority:high")')
    parser.add_argument('--assignee', help='Assign to user (@me for current user)')
    parser.add_argument('--repo', help='GitHub repo (default: coordination repo from config)')
    parser.add_argument('--no-project-board', action='store_true',
                       help='Skip adding to project board even if configured')
    parser.add_argument('--estimate', type=float,
                       help='Estimated hours (sets Planned time field)')
    parser.add_argument('--milestone',
                       help='Milestone name (e.g., "v2.0")')
    parser.add_argument('--start',
                       help='Start date (YYYY-MM-DD, +7d, +2w, or day name like "monday")')
    parser.add_argument('--target',
                       help='Target date (YYYY-MM-DD, +7d, +2w, or day name like "friday")')

    args = parser.parse_args()

    # Header
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}GitHub Issue Creator with Auto-Add to Project Board{RESET}")
    print(f"{BOLD}{'='*70}{RESET}")

    # Create the issue
    create_issue_with_board_sync(
        title=args.title,
        body=args.body,
        labels=args.labels,
        assignee=args.assignee,
        repo=args.repo,
        skip_board=args.no_project_board,
        estimate=args.estimate,
        milestone=args.milestone,
        start_date=args.start,
        target_date=args.target
    )

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Cancelled by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}✗ Unexpected error:{RESET} {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
