# PR Open Sync Snapshot

## Purpose

Generate a deterministic CSV-style snapshot of open PR evidence signals for release sync.

## Script

`./scripts/pr_open_sync_snapshot.sh`

Output columns:

- `number`
- `title`
- `url`
- `has_proposer_marker`
- `has_screenshot_command`
- `has_self_review`
- `has_rollout_note_ref`

## Requirements

- `gh` must be installed and authenticated for the current repo.
- `jq` must be installed.

The script fails loudly if dependencies or GitHub API calls are unavailable.

## Example

```bash
./scripts/pr_open_sync_snapshot.sh > artifacts/pr-open-sync-snapshot-$(date +%F).txt
```
