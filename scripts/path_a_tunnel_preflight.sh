#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/path_a_tunnel_preflight.sh \
    --host <target_host> \
    --port <target_port> \
    --ingress-url <https://public-ingress/health> \
    --credential-file <path>

Checks host resolution, TCP connectivity, ingress HTTP status, and credential file readability
before switching important PR public routes.
USAGE
}

log() {
  printf '[path-a-preflight] %s\n' "$*"
}

die() {
  log "ERROR: $*"
  exit 1
}

HOST=""
PORT=""
INGRESS_URL=""
CREDENTIAL_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="${2:-}"
      shift 2
      ;;
    --port)
      PORT="${2:-}"
      shift 2
      ;;
    --ingress-url)
      INGRESS_URL="${2:-}"
      shift 2
      ;;
    --credential-file)
      CREDENTIAL_FILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

[[ -n "$HOST" ]] || die "--host is required"
[[ -n "$PORT" ]] || die "--port is required"
[[ "$PORT" =~ ^[0-9]+$ ]] || die "--port must be numeric"
[[ -n "$INGRESS_URL" ]] || die "--ingress-url is required"
[[ -n "$CREDENTIAL_FILE" ]] || die "--credential-file is required"

for cmd in getent curl timeout sha256sum wc grep awk; do
  command -v "$cmd" >/dev/null 2>&1 || die "missing required command: $cmd"
done

log "checking host lookup: $HOST"
if ! host_line="$(getent hosts "$HOST" | head -n 1)"; then
  die "host lookup failed for $HOST"
fi
[[ -n "$host_line" ]] || die "host lookup returned empty result for $HOST"
log "host resolved: $host_line"

log "checking tcp connectivity: ${HOST}:${PORT}"
timeout 5 bash -c "cat < /dev/null > /dev/tcp/${HOST}/${PORT}" || die "tcp connection failed to ${HOST}:${PORT}"
log "tcp connectivity ok"

log "checking ingress endpoint: $INGRESS_URL"
if ! http_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "$INGRESS_URL")"; then
  die "ingress request failed: $INGRESS_URL"
fi
# @@@ingress-status-window - treat 2xx/3xx as preflight-safe responses before cutover.
if [[ "$http_code" -ge 200 && "$http_code" -lt 400 ]]; then
  log "ingress status ok: $http_code"
else
  die "unexpected ingress status: $http_code from $INGRESS_URL"
fi

log "checking credential file: $CREDENTIAL_FILE"
[[ -r "$CREDENTIAL_FILE" ]] || die "credential file not readable: $CREDENTIAL_FILE"
[[ -s "$CREDENTIAL_FILE" ]] || die "credential file is empty: $CREDENTIAL_FILE"
non_comment_lines="$(grep -Ev '^[[:space:]]*(#|$)' "$CREDENTIAL_FILE" | wc -l | awk '{print $1}')"
[[ "$non_comment_lines" -gt 0 ]] || die "credential file has no usable entries: $CREDENTIAL_FILE"
# @@@credential-fingerprint - print deterministic fingerprint instead of credential values.
cred_size="$(wc -c < "$CREDENTIAL_FILE" | awk '{print $1}')"
cred_sha="$(sha256sum "$CREDENTIAL_FILE" | awk '{print $1}')"
log "credential file ok: bytes=$cred_size sha256=$cred_sha entries=$non_comment_lines"

log "preflight passed for route switch"
