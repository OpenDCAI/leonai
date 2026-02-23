# Proposer Marker Check

Tiny utility to surface open PR metadata entries that are missing `[proposer:<id>]`.

## Usage

```bash
gh pr list --state open --limit 200 --json number,title,body,url > artifacts/open_pr_metadata.json
python3 scripts/check_pr_proposer_markers.py --input artifacts/open_pr_metadata.json
```

To make missing markers fail with exit code 1:

```bash
python3 scripts/check_pr_proposer_markers.py --input artifacts/open_pr_metadata.json --fail-on-missing
```

## Policy Applied

A PR passes when either location has a marker:
- Title includes `[proposer:<id>]`
- First non-empty body line includes `[proposer:<id>]`
