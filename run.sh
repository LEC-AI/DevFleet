#!/usr/bin/env bash
# Run backend + frontend for local dev.
#
#   ./run.sh              start both (frees the ports first)
#   ./run.sh --backend    API only
#   ./run.sh --frontend   UI only
#   ./run.sh --stop       just free the ports and exit
#
# Installs deps only when they've actually changed (hash-stamped), so a normal
# start is fast. Ctrl-C stops both.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

API_PORT="${DEVFLEET_API_PORT:-18801}"
UI_PORT="${DEVFLEET_UI_PORT:-3100}"
VENV=backend/.venv

c() { printf '\033[%sm%s\033[0m\n' "$1" "$2"; }
info() { c '36' "  $1"; }
warn() { c '33' "  $1"; }
die()  { c '31' "  $1"; exit 1; }

# ── Free a TCP port, whatever is holding it ────────────────────────────────
free_port() {
  local port=$1 pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids=$(lsof -ti "tcp:$port" 2>/dev/null || true)
  elif command -v fuser >/dev/null 2>&1; then
    pids=$(fuser -n tcp "$port" 2>/dev/null | tr -d ' ' || true)
  fi
  [ -z "$pids" ] && return 0
  warn "port $port busy (pid $(echo "$pids" | tr '\n' ' ')) — killing"
  kill $pids 2>/dev/null || true
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.3
    still=$(lsof -ti "tcp:$port" 2>/dev/null || true)
    [ -z "$still" ] && return 0
  done
  kill -9 $(lsof -ti "tcp:$port" 2>/dev/null) 2>/dev/null || true
  sleep 0.3
}

# ── Install deps only when the manifest changed ────────────────────────────
hash_of() { { shasum -a 256 "$1" 2>/dev/null || sha256sum "$1"; } | cut -d' ' -f1; }

setup_backend() {
  local py
  # pydantic 2.10 has no wheels for 3.14 yet; prefer a version that builds.
  for cand in python3.13 python3.12 python3; do
    command -v "$cand" >/dev/null 2>&1 && py="$cand" && break
  done
  [ -n "${py:-}" ] || die "no python3 found"

  if [ ! -d "$VENV" ]; then
    info "creating venv ($py)"
    "$py" -m venv "$VENV" || die "venv creation failed"
  fi

  local want stamp=$VENV/.reqs-sha
  want=$(hash_of backend/requirements.txt)
  if [ ! -f "$stamp" ] || [ "$(cat "$stamp")" != "$want" ]; then
    info "installing backend deps"
    "$VENV/bin/pip" install -q --upgrade pip >/dev/null 2>&1
    "$VENV/bin/pip" install -q -r backend/requirements.txt || die "pip install failed"
    echo "$want" > "$stamp"
  fi
}

setup_frontend() {
  command -v npm >/dev/null 2>&1 || die "npm not found"
  local want stamp=frontend/node_modules/.pkg-sha
  want=$(hash_of frontend/package.json)
  if [ ! -d frontend/node_modules ] || [ ! -f "$stamp" ] || [ "$(cat "$stamp")" != "$want" ]; then
    info "installing frontend deps"
    (cd frontend && npm install --silent) || die "npm install failed"
    echo "$want" > "$stamp"
  fi
}

# ── Args ───────────────────────────────────────────────────────────────────
DO_API=1; DO_UI=1
case "${1:-}" in
  --backend)  DO_UI=0 ;;
  --frontend) DO_API=0 ;;
  --stop)     free_port "$API_PORT"; free_port "$UI_PORT"; info "ports freed"; exit 0 ;;
  "")         ;;
  *)          die "unknown option: $1 (see header for usage)" ;;
esac

echo
c '1;36' "  Claude DevFleet"
echo

[ -f .env ] || warn ".env missing — copy .env.example and set CLAUDE_CODE_OAUTH_TOKEN"

PIDS=()
cleanup() {
  echo
  info "stopping"
  for p in "${PIDS[@]:-}"; do [ -n "$p" ] && kill "$p" 2>/dev/null || true; done
  wait 2>/dev/null
}
trap cleanup EXIT INT TERM

if [ "$DO_API" = 1 ]; then
  free_port "$API_PORT"
  setup_backend
  # .env drives the night window, spend caps and the OAuth token. Exported so
  # uvicorn's child agents inherit them.
  if [ -f .env ]; then set -a; . ./.env; set +a; fi
  info "API      → http://localhost:$API_PORT      (docs: /docs)"
  ( cd backend && exec "../$VENV/bin/python" -m uvicorn app:app \
      --host 0.0.0.0 --port "$API_PORT" --reload ) &
  PIDS+=($!)
fi

if [ "$DO_UI" = 1 ]; then
  free_port "$UI_PORT"
  setup_frontend
  info "UI       → http://localhost:$UI_PORT"
  ( cd frontend && exec npx vite --port "$UI_PORT" --strictPort ) &
  PIDS+=($!)
fi

echo
info "Ctrl-C to stop"
echo
wait
