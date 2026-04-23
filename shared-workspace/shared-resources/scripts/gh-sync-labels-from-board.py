#!/usr/bin/env python3
"""
Sync issue labels from project board status.

Reads Status field from project board and updates issue labels to match.
Status mapping is derived dynamically from:
- project-shared.yaml: label_name -> option_id
- Project board API: option_id -> display_name

Run manually or via agent when drift is suspected.

Usage:
    ./gh-sync-labels-from-board.py           # Sync all, dry-run
    ./gh-sync-labels-from-board.py --apply   # Actually apply changes
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from config_loader import load_config

def get_status_field_options(project_id: str) -> list:
    """Query Status field options from project board.

    Returns list of dicts: [{"id": "abc123", "name": "In Progress"}, ...]
    """
    query = '''
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          field(name: "Status") {
            ... on ProjectV2SingleSelectField {
              options {
                id
                name
              }
            }
          }
        }
      }
    }
    '''

    cmd = ['gh', 'api', 'graphql', '-f', f'query={query}', '-F', f'projectId={project_id}']
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)

    field = data.get('data', {}).get('node', {}).get('field')
    if not field:
        return []

    return field.get('options', [])


def build_status_mapping(config: dict, project_id: str) -> dict:
    """Build display_name -> label mapping from config + board API.

    Combines:
    - Config: label_name -> option_id (from project_fields.status.options)
    - Board API: option_id -> display_name

    Returns: display_name -> "status:label_name"
    """
    # Get label -> option_id from config
    status_options = config.get("project", {}).get("github", {}).get("project_fields", {}).get("status", {}).get("options", {})

    if not status_options:
        print("Warning: No status options configured in project-shared.yaml")
        return {}

    # Filter out None values (unconfigured options)
    status_options = {k: v for k, v in status_options.items() if v is not None}

    if not status_options:
        print("Warning: All status options are null in project-shared.yaml")
        return {}

    # Invert to option_id -> label
    id_to_label = {v: f"status:{k}" for k, v in status_options.items()}

    # Query board for option_id -> display_name
    field_options = get_status_field_options(project_id)

    if not field_options:
        print("Warning: Could not fetch Status field options from project board")
        return {}

    # Build display_name -> label
    mapping = {}
    for opt in field_options:
        option_id = opt["id"]
        display_name = opt["name"]
        if option_id in id_to_label:
            mapping[display_name] = id_to_label[option_id]

    return mapping


def get_project_items(project_id: str) -> list:
    """Query all items from project board with their Status and linked issue."""
    query = '''
    query($projectId: ID!, $cursor: String) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items(first: 100, after: $cursor) {
            pageInfo { hasNextPage endCursor }
            nodes {
              content {
                ... on Issue {
                  number
                  repository { nameWithOwner }
                  labels(first: 20) { nodes { name } }
                }
              }
              fieldValues(first: 10) {
                nodes {
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                    field { ... on ProjectV2SingleSelectField { name } }
                  }
                }
              }
            }
          }
        }
      }
    }
    '''

    items = []
    cursor = None

    while True:
        cmd = ['gh', 'api', 'graphql', '-f', f'query={query}', '-F', f'projectId={project_id}']
        if cursor:
            cmd.extend(['-F', f'cursor={cursor}'])

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        page = data['data']['node']['items']
        items.extend(page['nodes'])

        if not page['pageInfo']['hasNextPage']:
            break
        cursor = page['pageInfo']['endCursor']

    return items


def sync_labels(dry_run: bool = True):
    config = load_config()
    project_id = config["project"]["github"].get("project_board_id")

    if not project_id:
        print("Error: project_board_id not configured in project-shared.yaml")
        return 1

    print("Building status mapping from config...")
    status_mapping = build_status_mapping(config, project_id)

    if not status_mapping:
        print("Error: Could not build status mapping. Check project-shared.yaml and project board configuration.")
        return 1

    print(f"Mapped {len(status_mapping)} status(es): {', '.join(status_mapping.keys())}\n")

    print("Querying project board items...")
    items = get_project_items(project_id)
    print(f"Found {len(items)} items\n")

    updates = []

    for item in items:
        content = item.get('content')
        if not content or 'number' not in content:
            continue  # Skip drafts/PRs

        issue_num = content['number']
        repo = content['repository']['nameWithOwner']
        current_labels = [l['name'] for l in content.get('labels', {}).get('nodes', [])]
        current_status = next((l for l in current_labels if l.startswith('status:')), None)

        # Find Status field value
        board_status = None
        for fv in item.get('fieldValues', {}).get('nodes', []):
            if fv.get('field', {}).get('name') == 'Status':
                board_status = fv.get('name')
                break

        if not board_status:
            continue

        expected_label = status_mapping.get(board_status)
        if not expected_label:
            print(f"  #{issue_num}: Unknown board status '{board_status}'")
            continue

        if current_status != expected_label:
            updates.append({
                'repo': repo,
                'issue': issue_num,
                'from': current_status,
                'to': expected_label,
                'board_status': board_status
            })

    if not updates:
        print("All labels are in sync.")
        return 0

    print(f"{'[DRY RUN] ' if dry_run else ''}Found {len(updates)} label(s) to update:\n")

    applied = 0
    failed = 0

    for u in updates:
        print(f"  #{u['issue']} ({u['repo']}): {u['from'] or '(none)'} -> {u['to']}  (board: {u['board_status']})")

        if not dry_run:
            try:
                args = ['gh', 'issue', 'edit', str(u['issue']), '--repo', u['repo'], '--add-label', u['to']]
                subprocess.run(args, check=True, capture_output=True)

                if u['from']:
                    args = ['gh', 'issue', 'edit', str(u['issue']), '--repo', u['repo'], '--remove-label', u['from']]
                    subprocess.run(args, check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                print(f"    ⚠ Failed: {e.stderr.decode().strip() if e.stderr else e}")
                failed += 1
                continue
            applied += 1

    if dry_run:
        print(f"\nRun with --apply to make changes.")
    else:
        print(f"\n{applied} label(s) updated, {failed} failed.")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Sync issue labels from project board status")
    parser.add_argument("--apply", action="store_true", help="Actually apply changes (default: dry-run)")
    args = parser.parse_args()

    return sync_labels(dry_run=not args.apply)


if __name__ == "__main__":
    sys.exit(main())
