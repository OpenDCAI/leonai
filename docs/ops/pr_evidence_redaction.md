# PR Evidence Redaction

Use `scripts/pr_evidence_redact.sh` to sanitize PR evidence files before sharing.

## Behavior

- Redacts absolute local paths that start with `/home/` or `/tmp/`
- Redacts local/private URLs (`localhost`, `127.0.0.1`, RFC1918 IP URLs)
- Redacts known sensitive hostnames (`*.internal`, `*.local`, `*.lan`, `host.docker.internal`)
- Fails loudly when the input path is missing or unreadable

## Usage

```bash
scripts/pr_evidence_redact.sh <input-file> [output-file]
```

- Without `output-file`, redacted content is written to stdout.
- With `output-file`, redacted content is written to that file.

## Example

Input:

```text
PR URL: https://github.com/OpenDCAI/leonai/pull/123
Proof file: /home/ubuntu/Aria/Projects/leonai/artifacts/proof.md
Temp output: /tmp/evidence.txt
FE URL: http://127.0.0.1:5272/
Host: host.docker.internal
```

Output:

```text
PR URL: https://github.com/OpenDCAI/leonai/pull/123
Proof file: <REDACTED_PATH>
Temp output: <REDACTED_PATH>
FE URL: <REDACTED_LOCAL_URL>
Host: <REDACTED_HOST>
```
