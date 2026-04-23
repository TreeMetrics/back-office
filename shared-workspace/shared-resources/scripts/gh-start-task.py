#!/usr/bin/env python3
"""
Start or resume working on a GitHub issue (GitHub-first workflow).

This script is IDEMPOTENT - it handles both fresh starts and resuming existing work.

What it does:
1. Assigns the issue to you (if not already assigned)
2. Updates status to 'in-progress'
3. Creates working directory in personal/
4. Gets GitHub Project item ID (for time tracking)
5. Starts time tracking session
6. Saves to local-work.json

NOTE: This script does NOT create branches. Use gh-create-branch.py separately
      when you need a branch for code changes.

Usage:
    # Start a task (no branch created)
    ./gh-start-task.py 7 --agent my-agent

    # Resume existing work (idempotent - safe to re-run)
    ./gh-start-task.py 7 --agent my-agent

    # For code changes, create branch separately:
    ./gh-create-branch.py 7 --repo tm_api --worktree -d "feature_description"
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add script directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from local_work import LocalWork
from gh_helpers import GitHubHelper
from gh_time_tracking import GitHubTimeTracking, GitHubProjectFields
from config_loader import load_config


def get_coord_repo_root():
    """Get coordination repository root."""
    return Path(__file__).parent.parent.parent.parent


def main():
    parser = argparse.ArgumentParser(description="Start or resume working on a GitHub issue")
    parser.add_argument("issue", type=int, help="Issue number")
    parser.add_argument("--agent", required=True, help="Unique agent identifier")

    args = parser.parse_args()

    # Load config
    config = load_config()
    project_name = config["project"]["name"]
    coord_repo = config["project"]["coordination_repo"]["github"]
    project_board_id = config["project"]["github"].get("project_board_id")

    # Load project field config for status and date updates
    project_fields = config["project"]["github"].get("project_fields", {})
    status_config = project_fields.get("status", {})
    status_field_id = status_config.get("field_id")
    status_options = status_config.get("options", {})
    start_date_field_id = project_fields.get("start_date", {}).get("field_id")
    status_field_configured = (project_board_id and status_field_id and status_options)

    # Initialize helpers
    coord_repo_root = get_coord_repo_root()
    gh = GitHubHelper(coord_repo)
    local_work = LocalWork(coord_repo_root, project_name, coord_repo)

    issue_num = args.issue
    agent_id = args.agent

    # Check if resuming existing work
    existing_work = local_work.get_issue(str(issue_num))
    is_resuming = existing_work is not None

    if is_resuming:
        print(f"\n🔄 Resuming work on issue #{issue_num} with agent '{agent_id}'...\n")
    else:
        print(f"\n🚀 Starting fresh work on issue #{issue_num} with agent '{agent_id}'...\n")

    # Check if issue exists on GitHub
    try:
        issue = gh.get_issue(issue_num)
        print(f"Issue: {issue['title']}")
    except Exception as e:
        print(f"❌ Error: Could not find issue #{issue_num}: {e}", file=sys.stderr)
        return 1

    # Check if agent is already busy with a DIFFERENT issue
    if local_work.is_agent_busy(agent_id):
        existing_issues = local_work.find_issues_by_agent(agent_id)
        if str(issue_num) not in existing_issues:
            print(f"❌ Error: Agent '{agent_id}' is already assigned to issue(s): {', '.join(existing_issues)}", file=sys.stderr)
            print("   Release the agent first with: ./gh-release-agent.py", file=sys.stderr)
            return 1

    # Step 1: Assign issue to current user (if not already)
    print("1. Assigning issue to you...")
    try:
        gh.assign_issue(issue_num)
        print("   ✓ Assigned")
    except Exception as e:
        print(f"   ⚠️  Warning: Could not assign issue: {e}", file=sys.stderr)

    # Step 2: Update status to in-progress
    print("2. Updating status to 'in-progress'...")
    try:
        current_labels = [l["name"] for l in issue.get("labels", [])]
        status_labels = [l for l in current_labels if l.startswith("status:")]

        gh.update_labels(issue_num, add=["status:in-progress"], remove=status_labels if status_labels else None)
        print("   ✓ Status updated")
    except Exception as e:
        print(f"   ⚠️  Warning: Could not update status: {e}", file=sys.stderr)

    # Step 3: Create working directory in personal/
    working_dir = f"personal/{project_name.lower().replace(' ', '-')}-{issue_num}"
    working_dir_path = coord_repo_root / working_dir
    print(f"3. Creating working directory: {working_dir}")
    working_dir_path.mkdir(parents=True, exist_ok=True)
    print(f"   ✓ Created (or already exists)")

    # Step 4: Get GitHub Project item ID (for time tracking)
    github_project_item_id = None
    if project_board_id:
        print("4. Getting GitHub Project item ID...")
        try:
            time_tracker = GitHubTimeTracking(project_board_id)
            github_project_item_id = time_tracker.get_project_item_id_for_issue(issue_num, coord_repo)
            if github_project_item_id:
                print(f"   ✓ Found: {github_project_item_id}")

                # Also update project field status if configured
                if status_field_configured:
                    try:
                        fields = GitHubProjectFields(
                            project_board_id,
                            status_field_id=status_field_id,
                            status_options=status_options,
                            start_date_field_id=start_date_field_id
                        )
                        success = fields.update_status(github_project_item_id, "in-progress")
                        if success:
                            print(f"   ✓ Project field updated to 'in-progress'")
                        else:
                            print("   ⚠️  Could not update project field")

                        # Auto-set start_date to today if not already set
                        if start_date_field_id and not is_resuming:
                            current_start = fields.get_start_date(github_project_item_id)
                            if not current_start:
                                today = datetime.now().date().isoformat()
                                if fields.update_start_date(github_project_item_id, today):
                                    print(f"   ✓ Start date auto-set to {today}")
                                else:
                                    print("   ⚠️  Could not auto-set start date")
                            else:
                                print(f"   ℹ️  Start date already set ({current_start})")
                    except Exception as e:
                        print(f"   ⚠️  Project field update failed: {e}", file=sys.stderr)
            else:
                print(f"   ⚠️  Not found in project board (issue may not be added to project)")
        except Exception as e:
            print(f"   ⚠️  Warning: Could not get project item ID: {e}", file=sys.stderr)
    else:
        print("4. Skipping project board lookup (project_board_id not configured)")

    # Step 5: Save to local work and start time tracking
    # Preserve existing branch/worktree info if resuming
    branch_name = existing_work.get("branch") if existing_work else None
    worktree_path = existing_work.get("worktree") if existing_work else None
    code_repo_name = existing_work.get("code_repo") if existing_work else None

    print(f"5. Saving to local-work.json and starting time tracking...")
    try:
        local_work.start_work(
            str(issue_num),
            agent_id,
            code_repo=code_repo_name,
            branch=branch_name,
            worktree=worktree_path,
            working_dir=working_dir,
            github_project_item_id=github_project_item_id
        )
        print(f"   ✓ Work session started")
    except Exception as e:
        print(f"   ❌ Error saving local work: {e}", file=sys.stderr)
        return 1

    # Summary
    print(f"\n✅ Ready to work on issue #{issue_num}!")
    print(f"   Issue URL: {issue['url']}")
    print(f"   Working dir: {working_dir}")
    print(f"   Time tracking: ⏱️  Session started")

    if branch_name:
        print(f"   Branch: {branch_name}")
    if worktree_path:
        print(f"   Worktree: {worktree_path}")

    print(f"\n   When done, stop work with: ./gh-stop-work.py {issue_num}")

    if not branch_name:
        print(f"\n   Need a branch for code changes?")
        print(f"   ./gh-create-branch.py {issue_num} --repo <repo> -d \"description\"")

    return 0


if __name__ == "__main__":
    sys.exit(main())
