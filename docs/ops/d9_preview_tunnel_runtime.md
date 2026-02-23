# d9 Preview Tunnel Runtime (PR61 + PR66)

This runbook keeps the d9 Cloudflare Tunnel runtime persistent and observable for the Alibaba <-> ZGC preview path:

- `pr61-leon.f2j.space`
- `pr66-leon.f2j.space`

When the d9 process exits, Cloudflare returns `HTTP 530` with edge error `1033`. The script below keeps one `cloudflared` child alive and auto-restarts it on exit.

## 1) Start persistent runtime

```bash
./scripts/d9_preview_tunnel_runtime.sh start
```

Defaults:

- `D9_TUNNEL_ID=d9c1137e-a397-40bc-9774-f41ff36e13d5`
- `D9_PREVIEW_HOSTS="pr61-leon.f2j.space pr66-leon.f2j.space"`
- `D9_LOCAL_PORT=5272`
- `D9_TUNNEL_CREDENTIALS_FILE=~/.cloudflared/<D9_TUNNEL_ID>.json`

## 2) Observe runtime

```bash
./scripts/d9_preview_tunnel_runtime.sh status
```

Observability outputs:

- supervisor/cloudflared pid + running state
- restart event count (`restart_events`)
- recent supervisor log tail
- recent cloudflared log tail

Artifacts are written to:

- `artifacts/d9-preview-tunnel/supervisor.log`
- `artifacts/d9-preview-tunnel/cloudflared.log`
- `artifacts/d9-preview-tunnel/cloudflared-d9.yml`

## 3) Health check preview endpoints

```bash
./scripts/d9_preview_tunnel_runtime.sh health
```

The command prints one compact signature line per host:

```text
health host=<host> status=<http_status> cf_ray=<cf_ray> headers=<artifact_path>
```

Expected healthy state: both hosts are `status=200`.

If any host is not `200` (for example `530`), the command exits non-zero and fails loudly.

## 4) Stop runtime

```bash
./scripts/d9_preview_tunnel_runtime.sh stop
```
