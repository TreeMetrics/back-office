#!/usr/bin/env python3
"""
Project Configuration Loader

Loads project configuration from split files:
- project-shared.yaml (tracked in git): Shared constants like GitHub field IDs
- project-local.yaml (gitignored): Personal settings like local file paths

Benefits:
1. Single source of truth for shared constants (in git)
2. Zero configuration drift between team members
3. Updates to GitHub field IDs distributed via git pull
4. Simpler onboarding (only configure personal paths)

Usage:
    from config_loader import load_config

    config = load_config()
    org = config['project']['github']['org']
"""

import os
from pathlib import Path
from typing import Dict, Any, List
import yaml


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with override taking precedence.

    For lists of dictionaries with 'name' keys (like code_repositories),
    merges by name rather than replacing the entire list.

    Args:
        base: Base dictionary (shared config)
        override: Override dictionary (local config)

    Returns:
        Merged dictionary

    Examples:
        >>> base = {'a': 1, 'b': {'c': 2}}
        >>> override = {'b': {'d': 3}, 'e': 4}
        >>> deep_merge(base, override)
        {'a': 1, 'b': {'c': 2, 'd': 3}, 'e': 4}

        >>> base = {'repos': [{'name': 'r1', 'url': 'u1'}]}
        >>> override = {'repos': [{'name': 'r1', 'path': 'p1'}]}
        >>> deep_merge(base, override)
        {'repos': [{'name': 'r1', 'url': 'u1', 'path': 'p1'}]}
    """
    result = base.copy()

    for key, value in override.items():
        if key not in result:
            # Key only in override, add it
            result[key] = value
        elif isinstance(result[key], dict) and isinstance(value, dict):
            # Both are dicts, recurse
            result[key] = deep_merge(result[key], value)
        elif isinstance(result[key], list) and isinstance(value, list):
            # Both are lists - check if they're lists of dicts with 'name' key
            if (result[key] and isinstance(result[key][0], dict) and
                'name' in result[key][0] and
                value and isinstance(value[0], dict) and
                'name' in value[0]):
                # Merge lists by 'name' field (e.g., code_repositories)
                merged = {item['name']: item.copy() for item in result[key]}
                for item in value:
                    name = item['name']
                    if name in merged:
                        # Merge this item with existing
                        merged[name] = deep_merge(merged[name], item)
                    else:
                        # New item, add it
                        merged[name] = item.copy()
                result[key] = list(merged.values())
            else:
                # Not mergeable lists, override wins
                result[key] = value
        else:
            # Scalar or incompatible types, override wins
            result[key] = value

    return result


def expand_paths(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively expand ~ and environment variables in path strings.

    Args:
        config: Configuration dictionary

    Returns:
        Configuration with expanded paths
    """
    if isinstance(config, dict):
        return {k: expand_paths(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [expand_paths(item) for item in config]
    elif isinstance(config, str):
        # Expand ~ and environment variables in strings
        if '~' in config or '$' in config:
            return os.path.expanduser(os.path.expandvars(config))
        return config
    else:
        return config


def find_repo_root() -> Path:
    """
    Find the repository root directory by walking up from the script location.

    Returns:
        Path to repository root

    Raises:
        FileNotFoundError: If repo root cannot be found
    """
    current = Path(__file__).parent.resolve()
    for _ in range(10):  # Safety limit
        if (current / "project-shared.yaml").exists():
            return current
        if current.parent == current:  # Reached filesystem root
            break
        current = current.parent

    raise FileNotFoundError(
        "Cannot find repository root. Expected to find project-shared.yaml "
        "in a parent directory of the script."
    )


def load_config() -> Dict[str, Any]:
    """
    Load project configuration from split files.

    Returns:
        Merged configuration dictionary

    Raises:
        FileNotFoundError: If configuration files not found
    """
    repo_root = find_repo_root()

    shared_config_path = repo_root / "project-shared.yaml"
    local_config_path = repo_root / "project-local.yaml"

    # Load shared config (tracked in git)
    if not shared_config_path.exists():
        raise FileNotFoundError(
            f"Shared config not found: {shared_config_path}\n"
            f"Expected project-shared.yaml in repository root."
        )

    with open(shared_config_path, 'r') as f:
        shared = yaml.safe_load(f) or {}

    # Load local config (gitignored)
    if not local_config_path.exists():
        raise FileNotFoundError(
            f"Local config not found: {local_config_path}\n\n"
            f"Setup required:\n"
            f"  1. cp project-local.yaml.template project-local.yaml\n"
            f"  2. Edit project-local.yaml with your personal paths\n"
            f"  3. Run script again"
        )

    with open(local_config_path, 'r') as f:
        local = yaml.safe_load(f) or {}

    # Merge: shared as base, local overrides
    config = deep_merge(shared, local)

    # Expand ~ and env vars in paths
    config = expand_paths(config)
    return config


def get_coordination_repo(config: Dict[str, Any]) -> str:
    """
    Get coordination repository in 'Org/repo' format.

    Args:
        config: Project configuration

    Returns:
        Repository string (e.g., "TreeMetrics/coordination-template")
    """
    return config['project']['coordination_repo']['github']


def get_code_repo_config(config: Dict[str, Any], repo_name: str) -> Dict[str, Any]:
    """
    Get configuration for a specific code repository.

    Args:
        config: Project configuration
        repo_name: Name of repository (e.g., "backend", "tm_api")

    Returns:
        Repository configuration dict

    Raises:
        KeyError: If repository not found in config
    """
    repos = config.get('code_repositories', [])
    for repo in repos:
        if repo['name'] == repo_name:
            return repo

    raise KeyError(
        f"Repository '{repo_name}' not found in configuration. "
        f"Available: {[r['name'] for r in repos]}"
    )


# Convenience function for scripts that just need the repo
def get_repo() -> str:
    """
    Get coordination repository (convenience function).

    Returns:
        Repository string (e.g., "TreeMetrics/coordination-template")
    """
    config = load_config()
    return get_coordination_repo(config)


if __name__ == '__main__':
    # Test/debug: print loaded config
    import json
    try:
        config = load_config()
        print(json.dumps(config, indent=2))
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)
