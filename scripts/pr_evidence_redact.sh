#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "usage: $0 <input-file> [output-file]" >&2
  exit 1
fi

input_file="$1"
output_file="${2:-}"

if [[ ! -f "$input_file" ]]; then
  echo "input file not found: $input_file" >&2
  exit 1
fi

# @@@redaction-rules - Replace only sensitive path/host substrings so evidence keys remain intact.
redact() {
  perl -pe '
    s{(?<!\S)/home/[^\s`\"\)\]]+}{<REDACTED_PATH>}g;
    s{(?<!\S)/tmp/[^\s`\"\)\]]+}{<REDACTED_PATH>}g;
    s{\bhttps?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0)(?::\d+)?(?:/[^\s]*)?}{<REDACTED_LOCAL_URL>}gi;
    s{\bhttps?://(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})(?::\d+)?(?:/[^\s]*)?}{<REDACTED_PRIVATE_URL>}gi;
    s{\b(?:host\.docker\.internal|localhost)\b}{<REDACTED_HOST>}gi;
    s{\b(?:[A-Za-z0-9-]+\.)+(?:internal|local|lan)\b}{<REDACTED_HOST>}gi;
  '
}

if [[ -n "$output_file" ]]; then
  redact < "$input_file" > "$output_file"
else
  redact < "$input_file"
fi
