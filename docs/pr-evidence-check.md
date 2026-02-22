# PR Evidence Checker

Use `scripts/pr_evidence_check.sh` to validate PR markdown/comment evidence blocks.

## Usage

```bash
scripts/pr_evidence_check.sh <path_to_markdown_or_comment_blob>
```

or

```bash
cat <path_to_markdown_or_comment_blob> | scripts/pr_evidence_check.sh
```

## Required lines

```text
[proposer:hunter]
Screenshot URL: https://...
Artifact Path: /absolute/path/to/proof.md
Webshot Command: node /home/ubuntu/codex-smoke/tools/webshot.mjs http://127.0.0.1:5272/ /absolute/path/to/screenshot.png
Self-Review: I reviewed this PR evidence against all hard rules.
```

## Exit codes

- `0`: pass
- `10`: usage error
- `11`: input file read error
- `12`: empty input
- `21`: missing proposer marker
- `22`: missing screenshot URL line
- `23`: missing absolute artifact path line
- `24`: missing exact webshot command line
- `25`: missing self-review line
