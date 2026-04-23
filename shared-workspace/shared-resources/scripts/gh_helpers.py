#!/usr/bin/env python3
"""
GitHub API Helpers for GitHub-First Coordination

This module provides helper functions for interacting with GitHub via the `gh` CLI.
All operations use `gh` commands which handle authentication and API rate limiting.
"""

import json
import subprocess
from typing import Optional, List, Dict, Any


class GitHubHelper:
    """Helper class for GitHub operations via gh CLI."""

    def __init__(self, repo: str):
        """
        Initialize GitHub helper.

        Args:
            repo: GitHub repository in "Org/repo-name" format
        """
        self.repo = repo

    def _run_gh(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """
        Run a gh command.

        Args:
            args: Command arguments (excluding 'gh')
            check: Whether to raise on non-zero exit code

        Returns:
            CompletedProcess result
        """
        cmd = ["gh"] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check
        )
        return result

    def list_issues(self, labels: Optional[List[str]] = None,
                   assignee: Optional[str] = None,
                   milestone: Optional[str] = None,
                   state: str = "open",
                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        List issues with optional filters.

        Args:
            labels: List of labels to filter by (all must match)
            assignee: Filter by assignee (@me or username)
            milestone: Filter by milestone name
            state: Issue state (open, closed, all)
            limit: Maximum number of issues to return

        Returns:
            List of issue dicts with number, title, labels, assignees, milestone, etc.
        """
        args = [
            "issue", "list",
            "--repo", self.repo,
            "--state", state,
            "--limit", str(limit),
            "--json", "number,title,labels,assignees,state,url,body,milestone,closedByPullRequestsReferences"
        ]

        if labels:
            for label in labels:
                args.extend(["--label", label])

        if assignee:
            args.extend(["--assignee", assignee])

        if milestone:
            args.extend(["--milestone", milestone])

        result = self._run_gh(args)
        return json.loads(result.stdout)

    def get_issue(self, issue_num: int) -> Dict[str, Any]:
        """
        Get detailed information about a specific issue.

        Args:
            issue_num: Issue number

        Returns:
            Issue dict with full details
        """
        args = [
            "issue", "view", str(issue_num),
            "--repo", self.repo,
            "--json", "number,title,body,labels,assignees,state,url,closedByPullRequestsReferences"
        ]
        result = self._run_gh(args)
        return json.loads(result.stdout)

    def update_labels(self, issue_num: int, add: Optional[List[str]] = None,
                     remove: Optional[List[str]] = None) -> None:
        """
        Update issue labels.

        Args:
            issue_num: Issue number
            add: Labels to add
            remove: Labels to remove
        """
        if add:
            args = [
                "issue", "edit", str(issue_num),
                "--repo", self.repo,
                "--add-label", ",".join(add)
            ]
            self._run_gh(args)

        if remove:
            args = [
                "issue", "edit", str(issue_num),
                "--repo", self.repo,
                "--remove-label", ",".join(remove)
            ]
            self._run_gh(args)

    def assign_issue(self, issue_num: int, assignee: str = "@me") -> None:
        """
        Assign issue to a user.

        Args:
            issue_num: Issue number
            assignee: Username or @me for current user
        """
        args = [
            "issue", "edit", str(issue_num),
            "--repo", self.repo,
            "--add-assignee", assignee
        ]
        self._run_gh(args)

    def unassign_issue(self, issue_num: int, assignee: str = "@me") -> None:
        """
        Unassign issue from a user.

        Args:
            issue_num: Issue number
            assignee: Username or @me for current user
        """
        args = [
            "issue", "edit", str(issue_num),
            "--repo", self.repo,
            "--remove-assignee", assignee
        ]
        self._run_gh(args)

    def develop_issue(self, issue_num: int, branch_repo: Optional[str] = None,
                     base: str = "main", checkout: bool = True,
                     name: Optional[str] = None) -> str:
        """
        Create a linked branch for an issue using gh issue develop.

        Args:
            issue_num: Issue number
            branch_repo: Repository to create branch in (default: same as issue repo)
            base: Base branch name
            checkout: Whether to checkout the new branch
            name: Custom branch name (if not provided, gh generates from issue title)

        Returns:
            Branch name that was created
        """
        args = [
            "issue", "develop", str(issue_num),
            "--repo", self.repo,
            "--base", base
        ]

        if name:
            args.extend(["--name", name])

        if branch_repo:
            args.extend(["--branch-repo", branch_repo])

        if checkout:
            args.append("--checkout")

        result = self._run_gh(args)

        # Parse branch name from output
        # Output format: First line is github.com/.../<repo>/tree/<branch-name>
        # or stderr contains "* [new branch] <branch-name> -> origin/<branch-name>"

        # Try parsing from URL on stdout first
        if result.stdout.strip():
            first_line = result.stdout.split('\n')[0]
            if '/tree/' in first_line:
                # Extract branch name from URL
                branch_name = first_line.split('/tree/')[-1].strip()
                return branch_name

        # Fallback: parse from stderr git output
        for line in result.stderr.split('\n'):
            if '[new branch]' in line:
                # Format: " * [new branch]      <branch-name> -> origin/<branch-name>"
                parts = line.split()
                if len(parts) >= 4:
                    return parts[3]  # Branch name

        raise RuntimeError(f"Failed to parse branch name from gh output.\nstdout: {result.stdout}\nstderr: {result.stderr}")

    def get_linked_prs(self, issue_num: int) -> List[Dict[str, Any]]:
        """
        Get all PRs linked to an issue (from any repository).

        Args:
            issue_num: Issue number

        Returns:
            List of PR dicts from closedByPullRequestsReferences
        """
        issue = self.get_issue(issue_num)
        return issue.get("closedByPullRequestsReferences", [])

    def create_pr(self, title: str, body: str = "", base: str = "main",
                 head: Optional[str] = None, repo: Optional[str] = None) -> str:
        """
        Create a pull request.

        Args:
            title: PR title
            body: PR description
            base: Base branch
            head: Head branch (default: current branch)
            repo: Target repository (default: self.repo)

        Returns:
            PR URL
        """
        target_repo = repo or self.repo

        args = [
            "pr", "create",
            "--repo", target_repo,
            "--base", base,
            "--title", title,
            "--body", body
        ]

        if head:
            args.extend(["--head", head])

        result = self._run_gh(args)
        # gh pr create outputs the PR URL
        return result.stdout.strip()

    def get_current_user(self) -> str:
        """Get the current authenticated GitHub username."""
        result = self._run_gh(["api", "user", "--jq", ".login"])
        return result.stdout.strip()

    def get_repo_default_branch(self, repo: Optional[str] = None) -> str:
        """
        Get the default branch for a repository.

        Args:
            repo: Repository in "Org/repo" format (default: self.repo)

        Returns:
            Default branch name
        """
        target_repo = repo or self.repo
        result = self._run_gh([
            "repo", "view", target_repo,
            "--json", "defaultBranchRef",
            "--jq", ".defaultBranchRef.name"
        ])
        return result.stdout.strip()

    def create_issue(self, title: str, body: str = "", labels: Optional[List[str]] = None,
                    assignee: Optional[str] = None, milestone: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new issue.

        Args:
            title: Issue title
            body: Issue description
            labels: List of labels to add
            assignee: Username to assign (@me for current user)
            milestone: Milestone name to add issue to

        Returns:
            Dict with issue details including 'number' and 'url'
        """
        args = [
            "issue", "create",
            "--repo", self.repo,
            "--title", title,
            "--body", body if body else ""
        ]

        if labels:
            args.extend(["--label", ",".join(labels)])

        if assignee:
            args.extend(["--assignee", assignee])

        if milestone:
            args.extend(["--milestone", milestone])

        # gh issue create outputs the URL
        result = self._run_gh(args)
        issue_url = result.stdout.strip()

        # Extract issue number from URL
        # Format: https://github.com/org/repo/issues/123
        issue_num = int(issue_url.rstrip('/').split('/')[-1])

        # Return dict with number, url, and title
        return {
            "number": issue_num,
            "url": issue_url,
            "title": title
        }

    def list_milestones(self, state: str = "open") -> List[Dict[str, Any]]:
        """
        List milestones for the repository.

        Args:
            state: "open", "closed", or "all"

        Returns:
            List of milestone dicts with title, due_on, open_issues, closed_issues
        """
        # Use state parameter in API call instead of jq filter to avoid escaping issues
        state_param = "" if state == "all" else f"?state={state}"
        result = self._run_gh([
            "api", f"repos/{self.repo}/milestones{state_param}"
        ])
        return json.loads(result.stdout) if result.stdout.strip() else []

    def add_issue_to_project(self, issue_url: str, project_id: int, org: str) -> bool:
        """
        Add an issue to a GitHub Project board.

        Args:
            issue_url: Full URL of the issue
            project_id: Project board ID (number)
            org: Organization name

        Returns:
            True if successful, False otherwise
        """
        args = [
            "project", "item-add", str(project_id),
            "--owner", org,
            "--url", issue_url
        ]

        try:
            self._run_gh(args, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
