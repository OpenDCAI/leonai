# HUNTER_GITHUB_ROLLOUT_020

- Proposer marker: `[proposer:hunter]`
- PR URL: https://github.com/OpenDCAI/leonai/pull/79
- Marker check artifact (absolute path): `/home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-pr-marker-check/artifacts/pr_marker_check_output.txt`
- Screenshot artifact (absolute path): `/home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-pr-marker-check/artifacts/leon-fe-home-20260223.png`

## Command Evidence

```bash
gh pr list --state open --limit 200 --json number,title,body,url > artifacts/open_pr_metadata.json
python3 scripts/check_pr_proposer_markers.py --input artifacts/open_pr_metadata.json | tee artifacts/pr_marker_check_output.txt
node /home/ubuntu/codex-smoke/tools/webshot.mjs http://127.0.0.1:5272/ /home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-pr-marker-check/artifacts/leon-fe-home-20260223.png
```

## Captured Output

- `Checked 3 open PR entries from artifacts/open_pr_metadata.json`
- `All entries include a proposer marker in title or first body line.`
- `screenshot_saved=/home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-pr-marker-check/artifacts/leon-fe-home-20260223.png`
