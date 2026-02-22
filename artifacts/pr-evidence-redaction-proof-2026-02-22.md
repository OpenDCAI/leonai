# PR Evidence Redaction Proof (2026-02-22)

## Scope

Added `scripts/pr_evidence_redact.sh` to sanitize PR evidence files by redacting local paths and sensitive host patterns.

## Command Evidence

### 1) Redaction success case

Command:

```bash
scripts/pr_evidence_redact.sh /tmp/pr-evidence-redaction-sample-2026-02-22.md > /tmp/pr-evidence-redaction-sample-2026-02-22.redacted.md
```

Redacted output:

```text
PR URL: https://github.com/OpenDCAI/leonai/pull/999
Proof file: <REDACTED_PATH>
Temp output: <REDACTED_PATH>
FE URL: <REDACTED_LOCAL_URL>
Private URL: <REDACTED_PRIVATE_URL>
Host: <REDACTED_HOST>
Service host: <REDACTED_HOST>
```

### 2) Fail-loud missing file case

Command:

```bash
scripts/pr_evidence_redact.sh /tmp/does-not-exist-2026-02-22.md
```

Observed stderr + exit code:

```text
exit_code=1
input file not found: /tmp/does-not-exist-2026-02-22.md
```

### 3) Leon FE screenshot (required command format)

Command:

```bash
node /home/ubuntu/codex-smoke/tools/webshot.mjs http://127.0.0.1:5272/ /home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-pr-evidence-redact/artifacts/leon-fe-screenshot-2026-02-22.png
```

Observed output:

```text
screenshot_saved=/home/ubuntu/Aria/Projects/leonai/worktrees/desks/hunter-pr-evidence-redact/artifacts/leon-fe-screenshot-2026-02-22.png
```

Screenshot artifact:

- `artifacts/leon-fe-screenshot-2026-02-22.png`
