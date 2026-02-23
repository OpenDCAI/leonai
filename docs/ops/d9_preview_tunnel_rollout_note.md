[proposer:hunter] d9 preview tunnel persistent runtime rollout note

- Marker: `[proposer:hunter]`
- PR URL: `PR_URL_TO_FILL`
- Screenshot path: `/home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-pr-d9-persistent/artifacts/d9-preview-tunnel/leon-fe-20260223T0444Z.png`
- Screenshot command:
  - `node /home/ubuntu/codex-smoke/tools/webshot.mjs http://127.0.0.1:5272/ /home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-pr-d9-persistent/artifacts/d9-preview-tunnel/leon-fe-20260223T0444Z.png`

## Command Evidence

- Runtime status command:
  - `./scripts/d9_preview_tunnel_runtime.sh status`
  - Artifact: `/home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-pr-d9-persistent/artifacts/d9-preview-tunnel/status-20260223T0445Z.txt`
- Health verification command:
  - `./scripts/d9_preview_tunnel_runtime.sh health`
  - Artifact: `/home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-pr-d9-persistent/artifacts/d9-preview-tunnel/health-20260223T0445Z.txt`
  - Response signature:
    - `health host=pr61-leon.f2j.space status=403 cf_ray=9d2411024be52efc-LAX`
    - `health host=pr66-leon.f2j.space status=403 cf_ray=9d24110be99acbaf-LAX`
