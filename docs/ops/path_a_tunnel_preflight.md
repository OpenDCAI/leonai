# Path A Tunnel Preflight

Use `scripts/path_a_tunnel_preflight.sh` before switching important PR public routes on Alibaba <-> ZGC tunnel path.

## Required checks

- Host resolves with DNS.
- Target host/port accepts TCP connection.
- Public ingress URL returns HTTP `2xx` or `3xx`.
- Credential file exists, is non-empty, and has non-comment entries.

## Command

```bash
scripts/path_a_tunnel_preflight.sh \
  --host <tunnel_host> \
  --port <tunnel_port> \
  --ingress-url <public_ingress_url> \
  --credential-file <credential_file>
```

## Regression tests

```bash
uv run pytest tests/test_path_a_tunnel_preflight.py -q
```
