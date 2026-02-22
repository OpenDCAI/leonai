# Alibaba<->ZGC Tunnel Proof Tuple Utility

Run once against a public URL and print a strict deterministic tuple.

## Command

```bash
scripts/zgc_tunnel_tuple.sh <public_url> [meta_dir]
```

## Output Contract

- `TUPLE_URL=<url>`
- `TUPLE_CURL=<exact curl command used>`
- `TUPLE_SHA256=<response body sha256>`
- Optional when `meta_dir` is set:
- `TUPLE_STATUS_FILE=<path>`
- `TUPLE_HEADER_FILE=<path>`

The script fails loudly on network/HTTP errors (`curl --fail`).
