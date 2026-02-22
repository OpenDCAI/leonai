#!/usr/bin/env bash
set -euo pipefail

readonly EXIT_OK=0
readonly EXIT_USAGE=10
readonly EXIT_READ_ERROR=11
readonly EXIT_EMPTY_INPUT=12
readonly EXIT_MISSING_PROPOSER=21
readonly EXIT_MISSING_SCREENSHOT_URL=22
readonly EXIT_MISSING_ARTIFACT_PATH=23
readonly EXIT_MISSING_WEBSHOT_COMMAND=24
readonly EXIT_MISSING_SELF_REVIEW=25

usage() {
  cat <<'USAGE'
Usage:
  scripts/pr_evidence_check.sh <markdown_or_comment_file>
  cat evidence.md | scripts/pr_evidence_check.sh

Required fields in text blob:
  1) [proposer:<name>]
  2) Screenshot URL: <http(s) URL>
  3) Artifact Path: <absolute path>
  4) Webshot Command: node /home/ubuntu/codex-smoke/tools/webshot.mjs http://127.0.0.1:5272/ <absolute_output_png_path>
  5) Self-Review: <explicit statement>
USAGE
}

die() {
  local code="$1"
  shift
  echo "ERROR: $*" >&2
  exit "$code"
}

read_input() {
  if [[ "$#" -gt 1 ]]; then
    usage >&2
    die "$EXIT_USAGE" "expected 0 or 1 argument, got $#"
  fi

  if [[ "$#" -eq 1 ]]; then
    local input_file="$1"
    [[ -f "$input_file" ]] || die "$EXIT_READ_ERROR" "input file not found: $input_file"
    cat "$input_file"
    return
  fi

  if [[ -t 0 ]]; then
    usage >&2
    die "$EXIT_USAGE" "no input provided"
  fi

  cat
}

main() {
  local content
  content="$(read_input "$@")"

  [[ -n "${content//[[:space:]]/}" ]] || die "$EXIT_EMPTY_INPUT" "input is empty"

  if ! printf '%s\n' "$content" | grep -Eq '\[proposer:[^]]+\]'; then
    die "$EXIT_MISSING_PROPOSER" "missing proposer marker like [proposer:hunter]"
  fi

  if ! printf '%s\n' "$content" | grep -Eq '^Screenshot URL:[[:space:]]*https?://[^[:space:]]+$'; then
    die "$EXIT_MISSING_SCREENSHOT_URL" "missing screenshot URL line: Screenshot URL: https://..."
  fi

  if ! printf '%s\n' "$content" | grep -Eq '^Artifact Path:[[:space:]]*/[^[:space:]]+$'; then
    die "$EXIT_MISSING_ARTIFACT_PATH" "missing absolute artifact path line: Artifact Path: /abs/path/to/file"
  fi

  # @@@webshot_command_guard - enforce exact command prefix and absolute PNG output path.
  if ! printf '%s\n' "$content" | grep -Eq '^Webshot Command:[[:space:]]*`?node /home/ubuntu/codex-smoke/tools/webshot\.mjs http://127\.0\.0\.1:5272/ /[^[:space:]]+\.png`?$'; then
    die "$EXIT_MISSING_WEBSHOT_COMMAND" "missing exact webshot command format"
  fi

  if ! printf '%s\n' "$content" | grep -Eq '^Self-Review:[[:space:]]*.+$'; then
    die "$EXIT_MISSING_SELF_REVIEW" "missing explicit self-review line"
  fi

  echo "PR evidence check: PASS"
  exit "$EXIT_OK"
}

main "$@"
