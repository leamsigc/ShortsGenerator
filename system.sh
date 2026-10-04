#!/usr/bin/env bash
#
# ShortsGenerator backend manager.
#
# Always runs `python ./Backend/main.py` inside the `shortsgenerator` conda
# env, from the repo root, no matter which shell/env you launched it from.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ENV_NAME="shortsgenerator"
PORT="${API_PORT:-8080}"
LOG_FILE="$SCRIPT_DIR/backend.log"
REQ_FILE="$SCRIPT_DIR/requirements.txt"
ENV_FILE="$SCRIPT_DIR/environment.yml"

note() { printf '\033[1;36m[system.sh]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[system.sh]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[system.sh]\033[0m %s\n' "$*" >&2; exit 1; }

# ------------------------------------------------------------------ help ----
cmd_help() {
  cat <<EOF
Usage: ./system.sh <command> [options]

Runs the ShortsGenerator backend (Flask, port ${PORT}) inside the
'${ENV_NAME}' conda env. With no command, this help is shown.

Commands:
  start [options]    Start the backend in this terminal (foreground).
                     Verifies the conda env + dependencies first, then stops
                     any stale backend still holding the port (Flask's debug
                     reloader leaves a parent + child behind — that is how
                     "fixed" code can appear not to take effect).
  stop               Stop the backend listening on port ${PORT} (TERM, then
                     KILL if it lingers). Refuses to kill a foreign process
                     that merely happens to hold the port.
  restart [options]  stop, then start again. Same options as start.
  status             Show whether the backend is running on port ${PORT}
                     (pids + uptime), without touching anything.
  help               Show this help.

Options for start / restart:
  -d, --background   Detach instead of staying in the foreground: the backend
                     keeps running after you close the terminal. Output goes
                     to backend.log. A health check waits until the API
                     answers before this command returns.
      --no-kill      Do NOT stop an already running backend. If the port is
                     busy, start fails with a hint to run stop/restart
                     instead of killing anything silently.

Environment:
  API_PORT           Port to serve/stop/check (default: 8080).

Files:
  backend.log        Backend output (every start appends here).

Examples:
  ./system.sh                 Show this help.
  ./system.sh start           Start in this terminal (Ctrl+C stops it).
  ./system.sh start -d        Start detached (keeps running).
  ./system.sh stop            Stop the backend.
  ./system.sh restart -d      Restart detached.
  ./system.sh status          Is it running?
  API_PORT=8081 ./system.sh start -d
EOF
}

# ------------------------------------------------------------ port helpers ----
# Pids currently LISTENING on $PORT (any process).
port_pids() {
  ss -ltnpH "sport = :$PORT" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u || true
}

# Full command line of a pid (empty when already gone).
cmd_of() {
  tr '\0' ' ' < "/proc/$1/cmdline" 2>/dev/null || true
}

# Pids on $PORT that are our backend (Flask reloader parent + child).
backend_pids() {
  for pid in $(port_pids); do
    case "$(cmd_of "$pid")" in
      *Backend/main.py*) printf '%s\n' "$pid" ;;
    esac
  done
}

# ------------------------------------------------------------------ stop ----
cmd_stop() {
  local pids
  pids="$(backend_pids)"
  if [ -z "$pids" ]; then
    if [ -n "$(port_pids)" ]; then
      die "Port $PORT is held by another process (not the backend) — not touching it."
    fi
    note "Backend is not running on port $PORT."
    return 0
  fi
  for pid in $pids; do
    note "Stopping backend (pid $pid)…"
    kill "$pid" 2>/dev/null || true
    found=1
  done
  # Give them a moment, then escalate leftovers to KILL.
  for _ in $(seq 1 10); do
    local alive=""
    for pid in $pids; do
      kill -0 "$pid" 2>/dev/null && alive="$alive $pid"
    done
    [ -z "$alive" ] && break
    sleep 0.5
  done
  for pid in $pids; do
    if kill -0 "$pid" 2>/dev/null; then
      warn "pid $pid lingers — killing."
      kill -9 "$pid" 2>/dev/null || true
    fi
  done
  sleep 0.5
  if [ -z "$(backend_pids)" ]; then
    note "Backend stopped."
  else
    die "Could not stop all backend processes: $(backend_pids | tr '\n' ' ')"
  fi
}

# ---------------------------------------------------------------- status ----
cmd_status() {
  local pids
  pids="$(backend_pids)"
  if [ -z "$pids" ]; then
    if [ -n "$(port_pids)" ]; then
      echo "Port $PORT is busy, but NOT with the backend (pids: $(port_pids | tr '\n' ' '))."
    else
      echo "Backend is not running (port $PORT is free)."
    fi
    return 0
  fi
  echo "Backend is running on port $PORT:"
  for pid in $pids; do
    local etime
    etime="$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ' || echo '?')"
    echo "  pid $pid  uptime $etime"
  done
}

# ------------------------------------------------------ conda + dependencies -
# Needed only for start/restart (stop/status stay instant and conda-free).
ensure_env() {
  # Source conda non-interactively so this works from cron, sh, or a fresh
  # terminal that never ran `conda init`. Always source it: a conda executable
  # on PATH without the shell functions makes `conda activate` fail.
  for conda_sh in \
    "$HOME/miniconda3/etc/profile.d/conda.sh" \
    "$HOME/anaconda3/etc/profile.d/conda.sh" \
    "$HOME/mambaforge/etc/profile.d/conda.sh" \
    "$HOME/miniforge3/etc/profile.d/conda.sh" \
    "/opt/conda/etc/profile.d/conda.sh"; do
    if [ -f "$conda_sh" ]; then
      # shellcheck disable=SC1090
      . "$conda_sh"
      break
    fi
  done
  command -v conda >/dev/null 2>&1 || die "conda not found — install Miniconda/Anaconda first."

  if ! conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    [ -f "$ENV_FILE" ] || die "conda env '$ENV_NAME' missing and $ENV_FILE not found."
    note "Creating conda env '$ENV_NAME' from environment.yml (this can take a few minutes)…"
    conda env create -f "$ENV_FILE"
  fi

  # Activate the env exactly like `conda activate shortsgenerator` would.
  conda activate "$ENV_NAME"
  PYTHON="$(command -v python)"
  note "Python: $PYTHON"
  case "$PYTHON" in
    *"/envs/$ENV_NAME/"*) ;;
    *) die "Wrong environment activated ($PYTHON) — expected $ENV_NAME." ;;
  esac

  # Missing modules (secretstorage = yt-dlp Chrome cookies, google-genai =
  # Gemini API, g4f = free providers) are the usual cause of
  # "it broke after a restart".
  local missing
  missing="$("$PYTHON" - <<'PY'
import importlib
required = [
    "flask", "flask_cors", "dotenv", "termcolor", "requests",
    "yt_dlp", "secretstorage", "google.genai", "g4f",
    "moviepy", "cv2", "numpy",
]
missing = []
for name in required:
    try:
        importlib.import_module(name)
    except Exception:
        missing.append(name)
print(",".join(missing))
PY
)"
  if [ -n "$missing" ]; then
    [ -f "$REQ_FILE" ] || die "Missing modules: $missing (and no requirements.txt found)."
    warn "Missing modules: $missing — installing from requirements.txt…"
    "$PYTHON" -m pip install --quiet --upgrade pip
    "$PYTHON" -m pip install -r "$REQ_FILE"
  fi
}

# Stop stale backend processes so the new one can bind the port. With
# KILL_STALE=0 (--no-kill) a busy port is a fatal error instead.
kill_stale() {
  if [ "$KILL_STALE" = "0" ]; then
    if [ -n "$(port_pids)" ]; then
      die "Port $PORT is already busy (pids: $(port_pids | tr '\n' ' ')). Use './system.sh stop' or 'restart' first."
    fi
    return 0
  fi
  for _attempt in $(seq 1 20); do
    local pids
    pids="$(port_pids)"
    [ -z "$pids" ] && break
    local killed=0
    for pid in $pids; do
      local cmd
      cmd="$(cmd_of "$pid")"
      [ -z "$cmd" ] && continue  # vanished between ss and read
      case "$cmd" in
        *Backend/main.py*)
          note "Stopping stale backend (pid $pid) on port $PORT…"
          kill -9 "$pid" 2>/dev/null || true
          killed=1
          ;;
        *)
          die "Port $PORT is used by another process (pid $pid) — stop it first, or run with API_PORT=<other>."
          ;;
      esac
    done
    [ "$killed" = "1" ] || sleep 0.5
    sleep 0.5
  done
  if ss -ltnH "sport = :$PORT" 2>/dev/null | grep -q .; then
    die "Port $PORT still busy after cleanup."
  fi
}

start_foreground() {
  note "Starting backend on port $PORT (log: $LOG_FILE)"
  note "cwd=$SCRIPT_DIR  env=$ENV_NAME"
  echo "------------------------------------------------------------------" >>"$LOG_FILE"
  date '+%F %T starting backend (foreground)' >>"$LOG_FILE"
  "$PYTHON" -u ./Backend/main.py 2>&1 | tee -a "$LOG_FILE"
}

start_background() {
  note "Starting backend on port $PORT detached (log: $LOG_FILE)"
  echo "------------------------------------------------------------------" >>"$LOG_FILE"
  date '+%F %T starting backend (background)' >>"$LOG_FILE"
  setsid nohup "$PYTHON" -u ./Backend/main.py >>"$LOG_FILE" 2>&1 </dev/null &
  # Wait until the API actually answers (or give up loudly).
  local ok=0
  for _ in $(seq 1 45); do
    if curl -sf -m 3 "http://localhost:$PORT/api/clipper/llm/settings" >/dev/null 2>&1; then
      ok=1
      break
    fi
    sleep 1
  done
  if [ "$ok" = "1" ]; then
    note "Backend is up on port $PORT (pids: $(backend_pids | tr '\n' ' ')). Tail the log with: tail -f $LOG_FILE"
  else
    warn "Backend did not answer within 45s — check $LOG_FILE for the traceback."
    return 1
  fi
}

# ------------------------------------------------------------------ start ---
cmd_start() {
  ensure_env
  kill_stale
  if [ "$BACKGROUND" = "1" ]; then
    start_background
  else
    start_foreground
  fi
}

# ------------------------------------------------------------------- main ---
COMMAND="${1:-help}"
shift || true
BACKGROUND=0
KILL_STALE=1
for arg in "$@"; do
  case "$arg" in
    -d|--background) BACKGROUND=1 ;;
    --no-kill)       KILL_STALE=0 ;;
    -h|--help)       cmd_help; exit 0 ;;
    *) die "Unknown option: $arg (see './system.sh help')" ;;
  esac
done

case "$COMMAND" in
  start)   cmd_start ;;
  stop)    cmd_stop ;;
  restart) cmd_stop && cmd_start ;;
  status)  cmd_status ;;
  help|-h|--help) cmd_help ;;
  *) die "Unknown command: $COMMAND (see './system.sh help')" ;;
esac
