#!/usr/bin/env python3
"""
Local Work Management for GitHub-First Coordination

Manages local-work.json in the coordination repository root.
This file tracks local work metadata (agent assignments, worktrees, branches, time tracking)
and is gitignored - never committed.

Schema:
{
  "project": "qarlbo",
  "coordination_repo": "TreeMetrics/qarlbo",
  "last_updated": "2025-11-18T12:00:00Z",
  "issues": {
    "7": {
      "agent_id": "my-agent",
      "code_repo": "tm_api",
      "branch": "qarlbo_7_report_triggers",
      "worktree": "~/workspace/tm_api_dev/qarlbo_7",
      "working_dir": "personal/qarlbo-7",
      "started": "2025-11-17T14:00:00Z",
      "time_tracking": {
        "total_minutes": 150,
        "last_synced_to_github": "2025-11-17T16:30:00Z",
        "sessions": [
          {
            "start": "2025-11-17T14:00:00Z",
            "end": "2025-11-17T16:30:00Z",
            "minutes": 150
          }
        ]
      },
      "github_project_item_id": "PVTI_..."
    }
  }
}
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List


class LocalWork:
    """Manages local work metadata for a coordination project."""

    def __init__(self, coord_repo_path: Path, project_name: str, coordination_repo: str):
        """
        Initialize local work manager.

        Args:
            coord_repo_path: Path to coordination repository root
            project_name: Name of the coordination project
            coordination_repo: GitHub repository in "Org/repo" format
        """
        self.coord_repo_path = Path(coord_repo_path)
        self.project_name = project_name
        self.coordination_repo = coordination_repo

        # Local work file in repo root (gitignored)
        self.work_file = self.coord_repo_path / "local-work.json"

        # Load or initialize
        self.data = self._load()

    def _now(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()

    def _load(self) -> Dict[str, Any]:
        """Load local work data from file."""
        if self.work_file.exists():
            with open(self.work_file, 'r') as f:
                return json.load(f)
        else:
            # Initialize new file
            return {
                "project": self.project_name,
                "coordination_repo": self.coordination_repo,
                "last_updated": self._now(),
                "issues": {}
            }

    def _save(self):
        """Save local work data to file."""
        self.data["last_updated"] = self._now()
        with open(self.work_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def start_work(self, issue_num: str, agent_id: str,
                   code_repo: Optional[str] = None,
                   branch: Optional[str] = None,
                   worktree: Optional[str] = None,
                   working_dir: Optional[str] = None,
                   github_project_item_id: Optional[str] = None) -> None:
        """
        Start or resume work on an issue.

        Args:
            issue_num: Issue number (as string)
            agent_id: Unique agent identifier
            code_repo: Code repository name (e.g., "tm_api")
            branch: Branch name
            worktree: Worktree path
            working_dir: Working directory path (relative to coord repo)
            github_project_item_id: GitHub Project item ID for time sync
        """
        issue_key = str(issue_num)

        # Get existing or create new
        if issue_key in self.data["issues"]:
            issue_data = self.data["issues"][issue_key]
            # Resuming - keep existing time tracking
        else:
            issue_data = {
                "agent_id": agent_id,
                "started": self._now(),
                "time_tracking": {
                    "total_minutes": 0,
                    "last_synced_to_github": None,
                    "sessions": []
                }
            }
            self.data["issues"][issue_key] = issue_data

        # Update fields
        issue_data["agent_id"] = agent_id
        if code_repo:
            issue_data["code_repo"] = code_repo
        if branch:
            issue_data["branch"] = branch
        if worktree:
            issue_data["worktree"] = worktree
        if working_dir:
            issue_data["working_dir"] = working_dir
        if github_project_item_id:
            issue_data["github_project_item_id"] = github_project_item_id

        # Start new time tracking session
        session = {
            "start": self._now(),
            "end": None,
            "minutes": None
        }
        issue_data["time_tracking"]["sessions"].append(session)

        self._save()

    def stop_work(self, issue_num: str) -> Optional[int]:
        """
        Stop current work session on an issue.

        Args:
            issue_num: Issue number (as string)

        Returns:
            Minutes for completed session, or None if no active session
        """
        issue_key = str(issue_num)
        if issue_key not in self.data["issues"]:
            return None

        issue_data = self.data["issues"][issue_key]
        sessions = issue_data["time_tracking"]["sessions"]

        # Find active session (no end time)
        active_session = next((s for s in sessions if s["end"] is None), None)
        if not active_session:
            return None

        # Complete the session
        now = self._now()
        active_session["end"] = now

        # Calculate minutes
        start = datetime.fromisoformat(active_session["start"])
        end = datetime.fromisoformat(now)
        minutes = int((end - start).total_seconds() / 60)
        active_session["minutes"] = minutes

        # Update total
        issue_data["time_tracking"]["total_minutes"] += minutes

        self._save()
        return minutes

    def get_issue(self, issue_num: str) -> Optional[Dict[str, Any]]:
        """
        Get work data for an issue.

        Args:
            issue_num: Issue number (as string)

        Returns:
            Issue work data or None if not found
        """
        return self.data["issues"].get(str(issue_num))

    def get_active_session_minutes(self, issue_num: str) -> Optional[int]:
        """
        Get minutes elapsed in active session.

        Args:
            issue_num: Issue number (as string)

        Returns:
            Minutes elapsed or None if no active session
        """
        issue_data = self.get_issue(issue_num)
        if not issue_data:
            return None

        sessions = issue_data["time_tracking"]["sessions"]
        active_session = next((s for s in sessions if s["end"] is None), None)
        if not active_session:
            return None

        start = datetime.fromisoformat(active_session["start"])
        now = datetime.now(timezone.utc)
        return int((now - start).total_seconds() / 60)

    def update_github_sync(self, issue_num: str):
        """
        Mark that time has been synced to GitHub.

        Args:
            issue_num: Issue number (as string)
        """
        issue_key = str(issue_num)
        if issue_key in self.data["issues"]:
            self.data["issues"][issue_key]["time_tracking"]["last_synced_to_github"] = self._now()
            self._save()

    def release_agent(self, agent_id: str) -> List[str]:
        """
        Release an agent from all issues.

        Args:
            agent_id: Agent identifier to release

        Returns:
            List of issue numbers that were released
        """
        released = []
        for issue_num, issue_data in list(self.data["issues"].items()):
            if issue_data.get("agent_id") == agent_id:
                # Stop any active session
                self.stop_work(issue_num)
                # Remove issue entry
                del self.data["issues"][issue_num]
                released.append(issue_num)

        if released:
            self._save()

        return released

    def is_agent_busy(self, agent_id: str) -> bool:
        """
        Check if an agent is assigned to any issue.

        Args:
            agent_id: Agent identifier to check

        Returns:
            True if agent is assigned to at least one issue
        """
        return any(
            issue_data.get("agent_id") == agent_id
            for issue_data in self.data["issues"].values()
        )

    def find_issues_by_agent(self, agent_id: str) -> List[str]:
        """
        Find all issues assigned to an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            List of issue numbers
        """
        return [
            issue_num
            for issue_num, issue_data in self.data["issues"].items()
            if issue_data.get("agent_id") == agent_id
        ]

    def list_all_issues(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all issues with their work data.

        Returns:
            Dictionary of issue_num -> issue_data
        """
        return self.data["issues"].copy()
