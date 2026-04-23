#!/usr/bin/env python3
"""
Release an agent from its assigned issue.

This script:
1. Stops any active time tracking session (calls gh-stop-work logic)
2. Syncs logged time to GitHub Project (if configured)
3. Removes agent assignment from local work state

Does NOT unassign from GitHub or change labels - those operations are manual.

Usage:
    ./gh-release-agent.py my-agent-1
    ./gh-release-agent.py my-agent-1 --unassign  # Also unassign from GitHub
    ./gh-release-agent.py my-agent-1 --no-sync   # Skip GitHub time sync
"""

import argparse
import subprocess
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


def main():
    parser = argparse.ArgumentParser(description="Release an agent from its assigned issue")
    parser.add_argument("agent_id", help="Agent identifier to release")
    parser.add_argument("--unassign", action="store_true", help="Also unassign from GitHub")
    parser.add_argument("--no-sync", action="store_true", help="Skip syncing time to GitHub Project")

    args = parser.parse_args()

    # Load config
    config = load_config()
    project_name = config["project"]["name"]
    github_repo = config["project"]["coordination_repo"]["github"]

    # Initialize
    coord_repo_root = get_coord_repo_root()
    local_work = LocalWork(coord_repo_root, project_name, github_repo)
    gh = GitHubHelper(github_repo) if args.unassign else None

    agent_id = args.agent_id

    # Find issues assigned to this agent
    issues = local_work.find_issues_by_agent(agent_id)

    if not issues:
        print(f"ℹ️  Agent '{agent_id}' is not assigned to any issues.")
        return 0

    # Should only be one issue per agent, but handle list for safety
    issue_list = ', '.join(f'#{i}' for i in issues)
    print(f"Releasing agent '{agent_id}' from issue {issue_list}")

    # Step 1: Stop work and sync time for each issue (calls gh-stop-work logic)
    stop_work_script = script_dir / "gh-stop-work.py"
    for issue_num in issues:
        print(f"\n--- Stopping work on issue #{issue_num} ---")
        cmd = [sys.executable, str(stop_work_script), issue_num]
        if args.no_sync:
            cmd.append("--no-sync")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"⚠️  Warning: stop-work returned non-zero for issue #{issue_num}", file=sys.stderr)

    # Step 2: Optionally unassign from GitHub
    if args.unassign and gh:
        print("\nUnassigning from GitHub...")
        for issue_num in issues:
            try:
                gh.unassign_issue(int(issue_num))
                print(f"   ✓ Unassigned from issue #{issue_num}")
            except Exception as e:
                print(f"   ⚠️  Could not unassign from issue #{issue_num}: {e}", file=sys.stderr)

    # Step 3: Release from local work state
    released = local_work.release_agent(agent_id)

    print(f"\n✅ Agent '{agent_id}' released")
    print(f"   Issues released: {', '.join(f'#{i}' for i in released)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
