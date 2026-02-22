# Path A Tunnel Preflight Artifact

This artifact records one executable proof run and rollout evidence for `[proposer:hunter]`.

## Proof Command

```bash
python3 -m http.server 18080 --bind 127.0.0.1 >/tmp/path_a_http.log 2>&1 &
HTTP_PID=$!
trap 'kill "$HTTP_PID"' EXIT
cat >/tmp/path_a_creds.env <<'CREDS'
ALIBABA_ACCESS_KEY_ID=dummy-ak
ALIBABA_ACCESS_KEY_SECRET=dummy-sk
CREDS
scripts/path_a_tunnel_preflight.sh \
  --host 127.0.0.1 \
  --port 18080 \
  --ingress-url http://127.0.0.1:18080/ \
  --credential-file /tmp/path_a_creds.env
```

## Proof Output

```text
[path-a-preflight] checking host lookup: 127.0.0.1
[path-a-preflight] host resolved: 127.0.0.1       localhost
[path-a-preflight] checking tcp connectivity: 127.0.0.1:18080
[path-a-preflight] tcp connectivity ok
[path-a-preflight] checking ingress endpoint: http://127.0.0.1:18080/
[path-a-preflight] ingress status ok: 200
[path-a-preflight] checking credential file: /tmp/path_a_creds.env
[path-a-preflight] credential file ok: bytes=66 sha256=2179d4d189359b34dc424f43fe86781e2ffbf3241152db63e194477e7e560924 entries=2
[path-a-preflight] preflight passed for route switch
```

## Rollout Notes

- Marker: `[proposer:hunter]`
- PR URL: `https://github.com/OpenDCAI/leonai/pull/71`
- Screenshot absolute path: `/home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-tunnel-preflight/artifacts/screenshots/leon_fe_5272_path_a_preflight.png`
- Screenshot command evidence: `node /home/ubuntu/codex-smoke/tools/webshot.mjs http://127.0.0.1:5272/ /home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-tunnel-preflight/artifacts/screenshots/leon_fe_5272_path_a_preflight.png`

## HUNTER_GITHUB_ROLLOUT_019_20260222T123748Z_PR71
- PR URL: https://github.com/OpenDCAI/leonai/pull/71
- Screenshot path: /tmp/hunter-pr70-72-remed-20260222T123650Z/repo/artifacts/screenshots/leon_fe_5272_path_a_preflight.png
- Command: `node /home/ubuntu/codex-smoke/tools/webshot.mjs http://127.0.0.1:5272/ /tmp/hunter-pr70-72-remed-20260222T123650Z/repo/artifacts/screenshots/leon_fe_5272_path_a_preflight.png`
