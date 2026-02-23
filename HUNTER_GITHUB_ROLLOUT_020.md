[proposer:hunter]
# HUNTER_GITHUB_ROLLOUT_020_20260223T133700Z

- PR: https://github.com/OpenDCAI/leonai/pull/86
- Branch: hunter/pr-capacity-fill-9
- Screenshot target route: /
- Screenshot URL: https://raw.githubusercontent.com/OpenDCAI/leonai/desk/hunter-pr-evidence-redact/artifacts/hunter-pr9-root-20260223T133720Z.png
- Absolute screenshot path: /tmp/hunter-pr9-root-20260223T133720Z.png
- Exact command: `node /home/ubuntu/codex-smoke/tools/webshot.mjs http://127.0.0.1:5272/settings /tmp/hunter-pr9-root-20260223T133720Z.png`
- Canonical comment URL: https://github.com/OpenDCAI/leonai/pull/86#issuecomment-3944832016
- Self-review: Confirmed only masked non-empty sandbox secret fields are read-only; revealed/empty fields remain editable.

command_evidence:
- `test -f /tmp/hunter-pr9-root-20260223T133720Z.png` -> `PATH_OK`
- `curl -I --max-time 20 https://raw.githubusercontent.com/OpenDCAI/leonai/desk/hunter-pr-evidence-redact/artifacts/hunter-pr9-root-20260223T133720Z.png` -> `HTTP/2 200`
