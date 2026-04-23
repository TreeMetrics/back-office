---
name: release-agent
description: Release an agent when done working (stops time tracking, syncs to GitHub)
argument-hint: <agent-id>
---

Release agent $ARGUMENTS when finished working.

Run this command from the repo root:

```bash
./shared-workspace/shared-resources/scripts/gh-release-agent.py $ARGUMENTS
```

This will:
- Stop the active time tracking session
- Sync logged time to GitHub Project (if configured)
- Release the agent from local work state

Use `--no-sync` to skip GitHub time sync if needed.

Note: Releasing does NOT change the issue status. The issue stays at its current status (typically `ready-for-review`) for the human to advance through review → done.
