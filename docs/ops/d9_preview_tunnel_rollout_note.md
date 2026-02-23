[proposer:hunter] d9 preview tunnel persistent runtime rollout note (refreshed 2026-02-23 UTC)

- Marker: `[proposer:hunter]`
- Job ID: `PR78-QUALITY-20260223T051311Z`
- PR URL: `https://github.com/OpenDCAI/leonai/pull/78`

## Re-Verification (/settings, live)

- Host: `pr61-leon.f2j.space`
- Verification command:
  - `curl -sS --http2 -D '/tmp/leonai-pr78-refresh/artifacts/d9-preview-tunnel/health-pr61-leon_f2j_space-settings-20260223T051311Z.headers' -o '/tmp/leonai-pr78-refresh/artifacts/d9-preview-tunnel/health-pr61-leon_f2j_space-settings-20260223T051311Z.html' --max-time 20 'https://pr61-leon.f2j.space/settings'`
- URL: `https://pr61-leon.f2j.space/settings`
- Status/signature: `HTTP/2 200`, `sha256=d53a60be1fc03b78c554296471f62323ec7402ace7b98cff2a45d905d85be035`, `bytes=950`, `cf_ray=9d243b909c0008d0-LAX`

- Host: `pr66-leon.f2j.space`
- Verification command:
  - `curl -sS --http2 -D '/tmp/leonai-pr78-refresh/artifacts/d9-preview-tunnel/health-pr66-leon_f2j_space-settings-20260223T051311Z.headers' -o '/tmp/leonai-pr78-refresh/artifacts/d9-preview-tunnel/health-pr66-leon_f2j_space-settings-20260223T051311Z.html' --max-time 20 'https://pr66-leon.f2j.space/settings'`
- URL: `https://pr66-leon.f2j.space/settings`
- Status/signature: `HTTP/2 200`, `sha256=d53a60be1fc03b78c554296471f62323ec7402ace7b98cff2a45d905d85be035`, `bytes=950`, `cf_ray=9d243b9bd8516a27-LAX`

- Summary artifact: `/tmp/leonai-pr78-refresh/artifacts/d9-preview-tunnel/health-settings-20260223T051311Z.txt`

## Screenshot Evidence

- Refreshed screenshot command:
  - `node /home/ubuntu/codex-smoke/tools/webshot.mjs https://pr61-leon.f2j.space/settings /tmp/leonai-pr78-refresh/artifacts/d9-preview-tunnel/pr61-settings-webshot-20260223T051326Z.png`
- Refreshed screenshot absolute path:
  - `/tmp/leonai-pr78-refresh/artifacts/d9-preview-tunnel/pr61-settings-webshot-20260223T051326Z.png`
- Screenshot command output artifact:
  - `/tmp/leonai-pr78-refresh/artifacts/d9-preview-tunnel/pr61-settings-webshot-20260223T051326Z.stdout.txt`

- Existing mandatory screenshot URL validity command:
  - `curl -I -L --max-time 20 'https://raw.githubusercontent.com/OpenDCAI/leonai/hunter/d9-tunnel-persistent-observable/artifacts/d9-preview-tunnel/leon-fe-20260223T0444Z.png'`
- Existing mandatory screenshot URL status:
  - `HTTP/2 200`

## Self-review

I explicitly self-reviewed this refresh update. It changes only PR evidence artifacts and rollout documentation; no runtime logic or application behavior was modified. Evidence now reflects current live truth (`pr61` and `pr66` `/settings` both `HTTP/2 200` with expected HTML signature).

## Quality Gate

- Gate decision: `PASS`
- Reason: both required hosts return expected `HTTP/2 200` and matching signature hash; screenshot evidence is valid and refreshed with exact command and absolute path.
