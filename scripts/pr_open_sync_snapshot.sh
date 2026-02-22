#!/usr/bin/env bash
set -euo pipefail

for dep in gh jq; do
  if ! command -v "$dep" >/dev/null 2>&1; then
    echo "ERROR: missing dependency '$dep'" >&2
    exit 1
  fi
done

if ! repo_json="$(gh repo view --json nameWithOwner 2>/dev/null)"; then
  echo "ERROR: failed to resolve repository via gh. Check gh auth/context." >&2
  exit 1
fi

name_with_owner="$(jq -r '.nameWithOwner // empty' <<<"$repo_json")"
if [[ -z "$name_with_owner" || "$name_with_owner" != */* ]]; then
  echo "ERROR: invalid repository metadata from gh repo view" >&2
  exit 1
fi

owner="${name_with_owner%/*}"
repo="${name_with_owner#*/}"

if ! prs_json="$(gh pr list --state open --limit 200 --json number,title,url,body 2>/dev/null)"; then
  echo "ERROR: failed to list open PRs via gh" >&2
  exit 1
fi

csv_escape() {
  local value="$1"
  value="${value//$'\n'/ }"
  value="${value//$'\r'/ }"
  value="${value//\"/\"\"}"
  printf '"%s"' "$value"
}

echo "number,title,url,has_proposer_marker,has_screenshot_command,has_self_review,has_rollout_note_ref"

while IFS= read -r pr_json; do
  number="$(jq -r '.number' <<<"$pr_json")"
  title="$(jq -r '.title // ""' <<<"$pr_json")"
  url="$(jq -r '.url // ""' <<<"$pr_json")"
  body="$(jq -r '.body // ""' <<<"$pr_json")"

  if ! first_comment="$(gh api "repos/$owner/$repo/issues/$number/comments?per_page=1" --jq '.[0].body // ""' 2>/dev/null)"; then
    echo "ERROR: failed to fetch first comment for PR #$number" >&2
    exit 1
  fi

  # @@@evidence-window - compliance evidence may be in PR body or first comment, so scan both text blocks.
  evidence_blob="$body"$'\n'"$first_comment"

  has_proposer_marker=false
  if printf '%s\n%s\n' "$title" "$body" | grep -Eqi '\[proposer:[^]]+\]'; then
    has_proposer_marker=true
  fi

  has_screenshot_command=false
  if printf '%s' "$evidence_blob" | grep -Eq 'node /home/ubuntu/codex-smoke/tools/webshot\.mjs http://127\.0\.0\.1:5272/ /[^[:space:]]+'; then
    has_screenshot_command=true
  fi

  has_self_review=false
  if printf '%s' "$evidence_blob" | grep -Eqi '\bself[- ]review\b'; then
    has_self_review=true
  fi

  has_rollout_note_ref=false
  if printf '%s' "$evidence_blob" | grep -Eqi 'HUNTER_GITHUB_ROLLOUT_[0-9]+|rollout[[:space:]-]?notes?'; then
    has_rollout_note_ref=true
  fi

  printf '%s,%s,%s,%s,%s,%s,%s\n' \
    "$number" \
    "$(csv_escape "$title")" \
    "$(csv_escape "$url")" \
    "$has_proposer_marker" \
    "$has_screenshot_command" \
    "$has_self_review" \
    "$has_rollout_note_ref"
done < <(jq -c 'sort_by(.number)[]' <<<"$prs_json")
