#!/usr/bin/env python3
"""
GitHub Project Field Integration

Syncs status, time tracking, and other custom fields to GitHub Projects.
Uses field-type-based methods for maximum flexibility.
"""

import json
import subprocess
from typing import Optional, Dict, List


class GitHubProjectFields:
    """Manages GitHub Project custom field updates (status, time, etc.)."""

    def __init__(
        self,
        project_id: str,
        logged_time_field_id: Optional[str] = None,
        planned_time_field_id: Optional[str] = None,
        target_date_field_id: Optional[str] = None,
        start_date_field_id: Optional[str] = None,
        status_field_id: Optional[str] = None,
        status_options: Optional[Dict[str, str]] = None
    ):
        """
        Initialize GitHub project field manager.

        Args:
            project_id: GitHub Project ID (e.g., "PVT_kwDOAAzY884Arwin")
            logged_time_field_id: Field ID for "Logged time" custom field
            planned_time_field_id: Field ID for "Planned time" custom field
            target_date_field_id: Field ID for "Target date" custom field
            start_date_field_id: Field ID for "Start date" custom field
            status_field_id: Field ID for "Status" custom field
            status_options: Dict mapping status names to option IDs
                           e.g., {"in-progress": "47fc9ee4", "ready-for-review": "feee3889"}
        """
        self.project_id = project_id
        self.logged_time_field_id = logged_time_field_id
        self.planned_time_field_id = planned_time_field_id
        self.target_date_field_id = target_date_field_id
        self.start_date_field_id = start_date_field_id
        self.status_field_id = status_field_id
        self.status_options = status_options or {}

    # ============================================================================
    # Field-Type-Based Methods (Generic)
    # ============================================================================

    def update_number_field(self, item_id: str, field_id: str, value: float) -> bool:
        """
        Update any number field (time, count, etc.).

        Args:
            item_id: GitHub Project item ID (e.g., "PVTI_...")
            field_id: Field ID for the number field
            value: Numeric value to set

        Returns:
            True if successful, False otherwise
        """
        try:
            query = f'''
mutation {{
  updateProjectV2ItemFieldValue(
    input: {{
      projectId: "{self.project_id}"
      itemId: "{item_id}"
      fieldId: "{field_id}"
      value: {{
        number: {round(value, 2)}
      }}
    }}
  ) {{
    projectV2Item {{
      id
    }}
  }}
}}
'''
            result = subprocess.run(
                ['gh', 'api', 'graphql', '-f', f'query={query}'],
                capture_output=True,
                text=True,
                check=True
            )

            response = json.loads(result.stdout)
            return "errors" not in response

        except subprocess.CalledProcessError as e:
            print(f"Error updating number field: {e.stderr}")
            return False
        except json.JSONDecodeError as e:
            print(f"Error parsing GitHub response: {e}")
            return False

    def update_single_select_field(self, item_id: str, field_id: str, option_id: str) -> bool:
        """
        Update any single-select field (status, type, priority, etc.).

        Args:
            item_id: GitHub Project item ID (e.g., "PVTI_...")
            field_id: Field ID for the single-select field
            option_id: Option ID to select

        Returns:
            True if successful, False otherwise
        """
        try:
            query = f'''
mutation {{
  updateProjectV2ItemFieldValue(
    input: {{
      projectId: "{self.project_id}"
      itemId: "{item_id}"
      fieldId: "{field_id}"
      value: {{
        singleSelectOptionId: "{option_id}"
      }}
    }}
  ) {{
    projectV2Item {{
      id
    }}
  }}
}}
'''
            result = subprocess.run(
                ['gh', 'api', 'graphql', '-f', f'query={query}'],
                capture_output=True,
                text=True,
                check=True
            )

            response = json.loads(result.stdout)
            return "errors" not in response

        except subprocess.CalledProcessError as e:
            print(f"Error updating single-select field: {e.stderr}")
            return False
        except json.JSONDecodeError as e:
            print(f"Error parsing GitHub response: {e}")
            return False

    def update_date_field(self, item_id: str, field_id: str, date_str: str) -> bool:
        """
        Update any date field.

        Args:
            item_id: GitHub Project item ID (e.g., "PVTI_...")
            field_id: Field ID for the date field
            date_str: ISO date string (YYYY-MM-DD)

        Returns:
            True if successful, False otherwise
        """
        if not field_id:
            return False

        try:
            query = f'''
mutation {{
  updateProjectV2ItemFieldValue(
    input: {{
      projectId: "{self.project_id}"
      itemId: "{item_id}"
      fieldId: "{field_id}"
      value: {{
        date: "{date_str}"
      }}
    }}
  ) {{
    projectV2Item {{
      id
    }}
  }}
}}
'''
            result = subprocess.run(
                ['gh', 'api', 'graphql', '-f', f'query={query}'],
                capture_output=True,
                text=True,
                check=True
            )

            response = json.loads(result.stdout)
            return "errors" not in response

        except subprocess.CalledProcessError as e:
            print(f"Error updating date field: {e.stderr}")
            return False
        except json.JSONDecodeError as e:
            print(f"Error parsing GitHub response: {e}")
            return False

    def get_date_field(self, item_id: str, field_id: str) -> Optional[str]:
        """
        Get date field value.

        Args:
            item_id: GitHub Project item ID
            field_id: Field ID for the date field

        Returns:
            ISO date string (YYYY-MM-DD) or None if not available
        """
        if not field_id:
            return None

        try:
            query = f'''
{{
  node(id: "{item_id}") {{
    ... on ProjectV2Item {{
      fieldValues(first: 20) {{
        nodes {{
          ... on ProjectV2ItemFieldDateValue {{
            field {{ ... on ProjectV2Field {{ id }} }}
            date
          }}
        }}
      }}
    }}
  }}
}}
'''
            result = subprocess.run(
                ['gh', 'api', 'graphql', '-f', f'query={query}'],
                capture_output=True,
                text=True,
                check=True
            )

            response = json.loads(result.stdout)
            nodes = response.get("data", {}).get("node", {}).get("fieldValues", {}).get("nodes", [])

            for node in nodes:
                if node.get("field", {}).get("id") == field_id:
                    return node.get("date")

            return None

        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError):
            return None

    # ============================================================================
    # Convenience Wrappers (Field-Specific)
    # ============================================================================

    def update_status(self, item_id: str, status_name: str) -> bool:
        """
        Update status field by status name.

        Args:
            item_id: GitHub Project item ID
            status_name: Status name (e.g., "in-progress", "ready-for-review")

        Returns:
            True if successful, False otherwise
        """
        if not self.status_field_id:
            print("Warning: status_field_id not configured in project-shared.yaml")
            return False

        option_id = self.status_options.get(status_name)
        if not option_id:
            print(f"Warning: No option ID configured for status '{status_name}'")
            return False

        return self.update_single_select_field(item_id, self.status_field_id, option_id)

    def update_logged_time(self, item_id: str, hours: float) -> bool:
        """
        Update logged time field.

        Args:
            item_id: GitHub Project item ID
            hours: Total hours logged

        Returns:
            True if successful, False otherwise
        """
        if not self.logged_time_field_id:
            print("Warning: logged_time_field_id not configured in project-shared.yaml")
            return False

        return self.update_number_field(item_id, self.logged_time_field_id, hours)

    def update_planned_time(self, item_id: str, hours: float) -> bool:
        """
        Update planned time (estimate) field.

        Args:
            item_id: GitHub Project item ID
            hours: Estimated hours

        Returns:
            True if successful, False otherwise
        """
        if not self.planned_time_field_id:
            print("Warning: planned_time_field_id not configured in project-shared.yaml")
            return False

        return self.update_number_field(item_id, self.planned_time_field_id, hours)

    def update_target_date(self, item_id: str, date_str: str) -> bool:
        """
        Update target date field.

        Args:
            item_id: GitHub Project item ID
            date_str: ISO date string (YYYY-MM-DD)

        Returns:
            True if successful, False otherwise
        """
        if not self.target_date_field_id:
            print("Warning: target_date_field_id not configured in project-shared.yaml")
            return False

        return self.update_date_field(item_id, self.target_date_field_id, date_str)

    def update_start_date(self, item_id: str, date_str: str) -> bool:
        """
        Update start date field.

        Args:
            item_id: GitHub Project item ID
            date_str: ISO date string (YYYY-MM-DD)

        Returns:
            True if successful, False otherwise
        """
        if not self.start_date_field_id:
            print("Warning: start_date_field_id not configured in project-shared.yaml")
            return False

        return self.update_date_field(item_id, self.start_date_field_id, date_str)

    def get_start_date(self, item_id: str) -> Optional[str]:
        """
        Get start date field value.

        Args:
            item_id: GitHub Project item ID

        Returns:
            ISO date string (YYYY-MM-DD) or None if not set
        """
        if not self.start_date_field_id:
            return None

        return self.get_date_field(item_id, self.start_date_field_id)

    # ============================================================================
    # Batch Queries
    # ============================================================================

    def get_fields_for_issues_batch(self, issue_numbers: List[int], repo: str) -> Dict[int, Dict]:
        """
        Batch query Project fields for multiple issues.

        Args:
            issue_numbers: List of issue numbers
            repo: Repository in "Org/repo" format

        Returns:
            Dict mapping issue_number -> {planned_time, logged_time, target_date}
        """
        if not issue_numbers:
            return {}

        owner, repo_name = repo.split('/')

        # Build GraphQL query for all issues at once
        issue_queries = []
        for i, num in enumerate(issue_numbers):
            issue_queries.append(f'''
    issue{i}: repository(owner: "{owner}", name: "{repo_name}") {{
      issue(number: {num}) {{
        number
        projectItems(first: 5) {{
          nodes {{
            id
            project {{ id }}
            fieldValues(first: 10) {{
              nodes {{
                ... on ProjectV2ItemFieldNumberValue {{
                  field {{ ... on ProjectV2Field {{ id }} }}
                  number
                }}
                ... on ProjectV2ItemFieldDateValue {{
                  field {{ ... on ProjectV2Field {{ id }} }}
                  date
                }}
              }}
            }}
          }}
        }}
      }}
    }}''')

        query = "{" + "\n".join(issue_queries) + "\n}"

        try:
            result = subprocess.run(
                ['gh', 'api', 'graphql', '-f', f'query={query}'],
                capture_output=True,
                text=True,
                check=True
            )
            response = json.loads(result.stdout)
            data = response.get("data", {})

            results = {}
            for i, num in enumerate(issue_numbers):
                issue_data = data.get(f"issue{i}", {}).get("issue", {})
                if not issue_data:
                    continue

                # Find project item matching our project
                for item in issue_data.get("projectItems", {}).get("nodes", []):
                    if item.get("project", {}).get("id") != self.project_id:
                        continue

                    fields = {"planned_time": None, "logged_time": None, "target_date": None}
                    for fv in item.get("fieldValues", {}).get("nodes", []):
                        field_id = fv.get("field", {}).get("id")
                        if field_id == self.planned_time_field_id:
                            fields["planned_time"] = fv.get("number")
                        elif field_id == self.logged_time_field_id:
                            fields["logged_time"] = fv.get("number")
                        elif field_id == self.target_date_field_id:
                            fields["target_date"] = fv.get("date")

                    results[num] = fields
                    break

            return results

        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return {}

    # ============================================================================
    # Backwards Compatibility (Deprecated, use update_logged_time instead)
    # ============================================================================

    def sync_logged_time(self, item_id: str, hours: float) -> bool:
        """
        Sync logged time to GitHub Project.

        DEPRECATED: Use update_logged_time() instead.
        This method is kept for backwards compatibility.

        Args:
            item_id: GitHub Project item ID (e.g., "PVTI_...")
            hours: Total hours logged

        Returns:
            True if successful, False otherwise
        """
        return self.update_logged_time(item_id, hours)

    def get_logged_time(self, item_id: str) -> Optional[float]:
        """
        Get logged time from GitHub Project.

        Args:
            item_id: GitHub Project item ID

        Returns:
            Hours logged, or None if not available
        """
        if not self.logged_time_field_id:
            return None

        try:
            query = f'''
{{
  node(id: "{item_id}") {{
    ... on ProjectV2Item {{
      fieldValues(first: 20) {{
        nodes {{
          ... on ProjectV2ItemFieldNumberValue {{
            field {{
              ... on ProjectV2Field {{
                id
                name
              }}
            }}
            number
          }}
        }}
      }}
    }}
  }}
}}
'''
            result = subprocess.run(
                ['gh', 'api', 'graphql', '-f', f'query={query}'],
                capture_output=True,
                text=True,
                check=True
            )

            response = json.loads(result.stdout)
            nodes = response.get("data", {}).get("node", {}).get("fieldValues", {}).get("nodes", [])

            for node in nodes:
                field = node.get("field", {})
                if field.get("id") == self.logged_time_field_id:
                    return node.get("number")

            return None

        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError):
            return None

    def get_project_item_id_for_issue(self, issue_number: int, repo: str) -> Optional[str]:
        """
        Get GitHub Project item ID for an issue.

        Args:
            issue_number: Issue number
            repo: Repository in "Org/repo" format

        Returns:
            Project item ID or None if not found
        """
        try:
            # First get the issue node ID
            result = subprocess.run(
                ['gh', 'issue', 'view', str(issue_number), '--repo', repo, '--json', 'id'],
                capture_output=True,
                text=True,
                check=True
            )
            issue_data = json.loads(result.stdout)
            issue_id = issue_data.get("id")

            if not issue_id:
                return None

            # Then find the project item
            query = f'''
{{
  node(id: "{issue_id}") {{
    ... on Issue {{
      projectItems(first: 10) {{
        nodes {{
          id
          project {{
            id
          }}
        }}
      }}
    }}
  }}
}}
'''
            result = subprocess.run(
                ['gh', 'api', 'graphql', '-f', f'query={query}'],
                capture_output=True,
                text=True,
                check=True
            )

            response = json.loads(result.stdout)
            items = response.get("data", {}).get("node", {}).get("projectItems", {}).get("nodes", [])

            # Find item in our project
            for item in items:
                if item.get("project", {}).get("id") == self.project_id:
                    return item.get("id")

            return None

        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError):
            return None


# ============================================================================
# Backwards Compatibility Alias
# ============================================================================

# For scripts that still import GitHubTimeTracking
GitHubTimeTracking = GitHubProjectFields
