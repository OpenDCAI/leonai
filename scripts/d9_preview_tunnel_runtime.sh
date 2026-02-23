#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/artifacts/d9-preview-tunnel"
PREVIEW_HOSTS_RAW="${D9_PREVIEW_HOSTS:-pr61-leon.f2j.space pr66-leon.f2j.space}"
LOCAL_PORT="${D9_LOCAL_PORT:-5272}"
TUNNEL_ID="${D9_TUNNEL_ID:-d9c1137e-a397-40bc-9774-f41ff36e13d5}"
CREDENTIALS_FILE="${D9_TUNNEL_CREDENTIALS_FILE:-$HOME/.cloudflared/${TUNNEL_ID}.json}"
CLOUDFLARED_CONFIG_FILE="${RUN_DIR}/cloudflared-d9.yml"
SUPERVISOR_PID_FILE="${RUN_DIR}/supervisor.pid"
CLOUDFLARED_PID_FILE="${RUN_DIR}/cloudflared.pid"
SUPERVISOR_LOG_FILE="${RUN_DIR}/supervisor.log"
CLOUDFLARED_LOG_FILE="${RUN_DIR}/cloudflared.log"

usage() {
  cat <<USAGE
Usage:
  d9_preview_tunnel_runtime.sh start
  d9_preview_tunnel_runtime.sh run
  d9_preview_tunnel_runtime.sh stop
  d9_preview_tunnel_runtime.sh status
  d9_preview_tunnel_runtime.sh health

Environment:
  D9_PREVIEW_HOSTS               Space-separated hosts. Default: "pr61-leon.f2j.space pr66-leon.f2j.space"
  D9_LOCAL_PORT                  Local frontend port. Default: 5272
  D9_TUNNEL_ID                   Cloudflare tunnel UUID. Default: d9c1137e-a397-40bc-9774-f41ff36e13d5
  D9_TUNNEL_CREDENTIALS_FILE     Credentials JSON file path. Default: ~/.cloudflared/<D9_TUNNEL_ID>.json
USAGE
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

ensure_run_dir() {
  mkdir -p "$RUN_DIR"
}

read_pid() {
  local pid_file="$1"
  [[ -s "$pid_file" ]] || return 1
  tr -d '[:space:]' < "$pid_file"
}

pid_is_running() {
  local pid="$1"
  [[ -n "$pid" ]] || return 1
  kill -0 "$pid" 2>/dev/null
}

log_supervisor() {
  ensure_run_dir
  printf '%s %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$*" >> "$SUPERVISOR_LOG_FILE"
}

parse_preview_hosts() {
  local -n out_hosts_ref="$1"
  read -r -a out_hosts_ref <<< "$PREVIEW_HOSTS_RAW"
  [[ ${#out_hosts_ref[@]} -gt 0 ]] || die "D9_PREVIEW_HOSTS cannot be empty"
}

write_cloudflared_config() {
  local hosts=()
  parse_preview_hosts hosts

  cat > "$CLOUDFLARED_CONFIG_FILE" <<EOF_CFG
tunnel: ${TUNNEL_ID}
credentials-file: ${CREDENTIALS_FILE}
ingress:
EOF_CFG

  local host
  for host in "${hosts[@]}"; do
    cat >> "$CLOUDFLARED_CONFIG_FILE" <<EOF_CFG
  - hostname: ${host}
    service: http://127.0.0.1:${LOCAL_PORT}
EOF_CFG
  done

  cat >> "$CLOUDFLARED_CONFIG_FILE" <<'EOF_CFG'
  - service: http_status:404
EOF_CFG
}

ensure_prereqs() {
  require_cmd cloudflared
  require_cmd curl
  [[ -f "$CREDENTIALS_FILE" ]] || die "missing tunnel credentials file: $CREDENTIALS_FILE"
}

start_detached() {
  ensure_run_dir
  ensure_prereqs
  write_cloudflared_config

  local existing_pid
  existing_pid="$(read_pid "$SUPERVISOR_PID_FILE" || true)"
  if [[ -n "$existing_pid" ]] && pid_is_running "$existing_pid"; then
    die "supervisor already running (pid=$existing_pid)"
  fi

  : > "$SUPERVISOR_LOG_FILE"
  : > "$CLOUDFLARED_LOG_FILE"

  setsid bash -lc "cd \"$ROOT_DIR\" && exec \"$ROOT_DIR/scripts/d9_preview_tunnel_runtime.sh\" run" >> "$SUPERVISOR_LOG_FILE" 2>&1 < /dev/null &
  local supervisor_pid=$!
  echo "$supervisor_pid" > "$SUPERVISOR_PID_FILE"
  sleep 1

  pid_is_running "$supervisor_pid" || die "supervisor exited immediately"
  echo "started d9 tunnel supervisor pid=${supervisor_pid}"
}

run_supervisor() {
  ensure_run_dir
  ensure_prereqs
  write_cloudflared_config

  local supervisor_pid
  supervisor_pid="$$"
  echo "$supervisor_pid" > "$SUPERVISOR_PID_FILE"

  local stop_requested=0
  local child_pid=""

  stop_handler() {
    stop_requested=1
    if [[ -n "$child_pid" ]] && pid_is_running "$child_pid"; then
      kill "$child_pid" 2>/dev/null || true
      wait "$child_pid" 2>/dev/null || true
    fi
    rm -f "$CLOUDFLARED_PID_FILE" "$SUPERVISOR_PID_FILE"
    log_supervisor "event=supervisor_stop reason=signal"
    exit 0
  }
  trap stop_handler INT TERM

  local restart_count=0
  # @@@supervisor-loop - keep one cloudflared child alive; restart on exit so tunnel survives transient disconnects.
  while true; do
    log_supervisor "event=cloudflared_start restart_count=${restart_count}"
    cloudflared --no-autoupdate tunnel --config "$CLOUDFLARED_CONFIG_FILE" run >> "$CLOUDFLARED_LOG_FILE" 2>&1 &
    child_pid=$!
    echo "$child_pid" > "$CLOUDFLARED_PID_FILE"

    set +e
    wait "$child_pid"
    local exit_code=$?
    set -e

    rm -f "$CLOUDFLARED_PID_FILE"

    if [[ "$stop_requested" -eq 1 ]]; then
      log_supervisor "event=cloudflared_exit exit_code=${exit_code} reason=stop_requested"
      break
    fi

    log_supervisor "event=cloudflared_exit exit_code=${exit_code} action=restart"
    restart_count=$((restart_count + 1))
    sleep 2
  done

  rm -f "$SUPERVISOR_PID_FILE"
}

stop_all() {
  ensure_run_dir

  local cloudflared_pid
  cloudflared_pid="$(read_pid "$CLOUDFLARED_PID_FILE" || true)"
  if [[ -n "$cloudflared_pid" ]] && pid_is_running "$cloudflared_pid"; then
    kill "$cloudflared_pid" 2>/dev/null || true
  fi

  local supervisor_pid
  supervisor_pid="$(read_pid "$SUPERVISOR_PID_FILE" || true)"
  if [[ -n "$supervisor_pid" ]] && pid_is_running "$supervisor_pid"; then
    kill "$supervisor_pid" 2>/dev/null || true
    sleep 1
    if pid_is_running "$supervisor_pid"; then
      kill -9 "$supervisor_pid" 2>/dev/null || true
    fi
  fi

  rm -f "$SUPERVISOR_PID_FILE" "$CLOUDFLARED_PID_FILE"
  echo "stopped d9 tunnel supervisor"
}

status_cmd() {
  ensure_run_dir

  local supervisor_pid cloudflared_pid
  supervisor_pid="$(read_pid "$SUPERVISOR_PID_FILE" || true)"
  cloudflared_pid="$(read_pid "$CLOUDFLARED_PID_FILE" || true)"

  echo "run_dir=$RUN_DIR"
  echo "tunnel_id=$TUNNEL_ID"
  echo "local_port=$LOCAL_PORT"
  echo "preview_hosts=$PREVIEW_HOSTS_RAW"
  echo "config=$CLOUDFLARED_CONFIG_FILE"
  echo "supervisor_pid=${supervisor_pid:-missing}"
  echo "cloudflared_pid=${cloudflared_pid:-missing}"

  if [[ -n "$supervisor_pid" ]] && pid_is_running "$supervisor_pid"; then
    echo "supervisor_state=running"
  else
    echo "supervisor_state=stopped"
  fi

  if [[ -n "$cloudflared_pid" ]] && pid_is_running "$cloudflared_pid"; then
    echo "cloudflared_state=running"
  else
    echo "cloudflared_state=stopped"
  fi

  local restart_events=0
  if [[ -f "$SUPERVISOR_LOG_FILE" ]]; then
    restart_events="$(grep -c "event=cloudflared_exit" "$SUPERVISOR_LOG_FILE" || true)"
  fi
  echo "restart_events=$restart_events"

  if [[ -f "$SUPERVISOR_LOG_FILE" ]]; then
    echo "supervisor_log_tail:"
    tail -n 20 "$SUPERVISOR_LOG_FILE"
  fi

  if [[ -f "$CLOUDFLARED_LOG_FILE" ]]; then
    echo "cloudflared_log_tail:"
    tail -n 20 "$CLOUDFLARED_LOG_FILE"
  fi
}

health_cmd() {
  ensure_run_dir
  require_cmd curl

  local hosts=()
  parse_preview_hosts hosts

  local any_bad=0
  local host
  for host in "${hosts[@]}"; do
    local headers_file
    headers_file="${RUN_DIR}/health-${host//./_}-$(date -u +"%Y%m%dT%H%M%SZ").headers"

    if ! curl -sS -D "$headers_file" -o /dev/null "https://${host}/"; then
      echo "health host=${host} status=curl_error headers=${headers_file}"
      any_bad=1
      continue
    fi

    local http_status cf_ray
    http_status="$(awk 'toupper($1) ~ /^HTTP\// {code=$2} END{print code}' "$headers_file")"
    cf_ray="$(awk -F': ' 'tolower($1)=="cf-ray" {print $2}' "$headers_file" | tr -d '\r' | tail -n 1)"
    http_status="${http_status:-unknown}"
    cf_ray="${cf_ray:-none}"

    # @@@health-signature - print compact status signature for rollout note and PR comment evidence.
    echo "health host=${host} status=${http_status} cf_ray=${cf_ray} headers=${headers_file}"

    if [[ "$http_status" != "200" ]]; then
      any_bad=1
    fi
  done

  [[ "$any_bad" -eq 0 ]] || die "health check failed: expected HTTP 200 for all hosts"
}

cmd="${1:-}"
case "$cmd" in
  start)
    start_detached
    ;;
  run)
    run_supervisor
    ;;
  stop)
    stop_all
    ;;
  status)
    status_cmd
    ;;
  health)
    health_cmd
    ;;
  *)
    usage
    exit 1
    ;;
esac
