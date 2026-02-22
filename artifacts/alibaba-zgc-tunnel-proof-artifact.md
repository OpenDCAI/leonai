# Alibaba<->ZGC Tunnel E2E Proof Artifact

This file records one executable run of `scripts/zgc_tunnel_tuple.sh`.

## Proof Run

Command:

```bash
scripts/zgc_tunnel_tuple.sh https://www.aliyun.com/robots.txt /tmp/leonai-pr-zgc-tunnel-proof-20260222/artifacts/zgc-proof-meta
```

Output:

```text
TUPLE_URL=https://www.aliyun.com/robots.txt
TUPLE_CURL=curl --fail --silent --show-error --location --connect-timeout 10 --max-time 30 https://www.aliyun.com/robots.txt
TUPLE_SHA256=c2ec566a51bbab46329648aa2afb60e368c13aa1b0caecf105b1e7d4d1e1710c
TUPLE_STATUS_FILE=/tmp/leonai-pr-zgc-tunnel-proof-20260222/artifacts/zgc-proof-meta/status.txt
TUPLE_HEADER_FILE=/tmp/leonai-pr-zgc-tunnel-proof-20260222/artifacts/zgc-proof-meta/headers.txt
```
