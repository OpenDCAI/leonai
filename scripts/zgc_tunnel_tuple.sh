#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/zgc_tunnel_tuple.sh <public_url> [meta_dir]

Output (deterministic line order):
  TUPLE_URL=...
  TUPLE_CURL=...
  TUPLE_SHA256=...
  TUPLE_STATUS_FILE=...   # only when meta_dir is provided
  TUPLE_HEADER_FILE=...   # only when meta_dir is provided
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 64
fi

url="$1"
meta_dir="${2:-}"

curl_flags=(--fail --silent --show-error --location --connect-timeout 10 --max-time 30)
printf -v quoted_url '%q' "$url"
curl_cmd="curl ${curl_flags[*]} ${quoted_url}"

body_file="$(mktemp)"
trap 'rm -f "$body_file"' EXIT

if [[ -n "$meta_dir" ]]; then
  mkdir -p "$meta_dir"
  # @@@stable-meta-paths - fixed file names keep heartbeat tuple output stable across runs.
  status_file="$meta_dir/status.txt"
  header_file="$meta_dir/headers.txt"
  curl "${curl_flags[@]}" -D "$header_file" -o "$body_file" -w '%{http_code}\n' "$url" > "$status_file"
else
  curl "${curl_flags[@]}" -o "$body_file" "$url"
fi

hash_value="$(sha256sum "$body_file" | awk '{print $1}')"

echo "TUPLE_URL=$url"
echo "TUPLE_CURL=$curl_cmd"
echo "TUPLE_SHA256=$hash_value"

if [[ -n "$meta_dir" ]]; then
  echo "TUPLE_STATUS_FILE=$status_file"
  echo "TUPLE_HEADER_FILE=$header_file"
fi
