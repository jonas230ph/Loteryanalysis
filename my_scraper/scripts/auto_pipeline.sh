#!/usr/bin/env bash
#
# auto_pipeline.sh
#
# Reliable local automation wrapper for:
#   1. synchronize
#   2. cleanup stale outputs
#   3. run scraper
#   4. wait for pcso_results.json to exist and become stable
#   5. run analyze_pcso_results.py
#   6. run analyze_pcso_results.py --suggestions-per-game 5
#
# Concurrency behavior:
#   This script uses an exclusive flock lock. If another pipeline is running,
#   a new invocation waits for the current run to finish. This queues work and
#   prevents overlapping analyzer processes.
#
# Environment configuration:
#   PROJECT_ROOT        Default: parent directory of this script
#   SCRAPER_CMD         Default: "$PYTHON_BIN pcso_lottery_scraper.py"
#   SYNCHRONIZE_CMD     Default: "synchronize"
#   PATH_TO_ANALYZER    Default: "$PROJECT_ROOT/analyze_pcso_results.py"
#   RESULTS_FILE        Default: "$PROJECT_ROOT/pcso_results.json"
#   ANALYSIS_DIR        Default: "$PROJECT_ROOT/analysis_outputs"
#   LOG_FILE            Default: "$PROJECT_ROOT/logs/pipeline.log"
#   FILE_POLL_INTERVAL  Default: 2
#   STABILITY_SECONDS   Default: 5
#   VENV_PATH           Default: "$PROJECT_ROOT/pcso_env"
#   PYTHON_BIN          Default: "$VENV_PATH/bin/python" if present, else python3
#   LOCK_FILE           Default: "$PROJECT_ROOT/.pipeline.lock"
#   WAIT_TIMEOUT        Default: 600

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
VENV_PATH="${VENV_PATH:-$PROJECT_ROOT/pcso_env}"
if [[ -z "${PYTHON_BIN:-}" ]]; then
  if [[ -x "$VENV_PATH/bin/python" ]]; then
    PYTHON_BIN="$VENV_PATH/bin/python"
  else
    PYTHON_BIN="python3"
  fi
fi

SCRAPER_CMD="${SCRAPER_CMD:-$PYTHON_BIN pcso_lottery_scraper.py}"
SYNCHRONIZE_CMD="${SYNCHRONIZE_CMD:-synchronize}"
PATH_TO_ANALYZER="${PATH_TO_ANALYZER:-$PROJECT_ROOT/analyze_pcso_results.py}"
RESULTS_FILE="${RESULTS_FILE:-$PROJECT_ROOT/pcso_results.json}"
ANALYSIS_DIR="${ANALYSIS_DIR:-$PROJECT_ROOT/analysis_outputs}"
LOG_FILE="${LOG_FILE:-$PROJECT_ROOT/logs/pipeline.log}"
FILE_POLL_INTERVAL="${FILE_POLL_INTERVAL:-2}"
STABILITY_SECONDS="${STABILITY_SECONDS:-5}"
LOCK_FILE="${LOCK_FILE:-$PROJECT_ROOT/.pipeline.lock}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-600}"

mkdir -p "$(dirname "$LOG_FILE")" "$ANALYSIS_DIR"

log() {
  local level="$1"
  shift
  local message="$*"
  local timestamp
  timestamp="$(date '+%Y-%m-%d %H:%M:%S%z')"
  printf '%s [%s] %s\n' "$timestamp" "$level" "$message" | tee -a "$LOG_FILE" >&2
}

run_cmd() {
  local label="$1"
  shift
  log INFO "Starting: $label :: $*"
  set +e
  "$@" 2>&1 | while IFS= read -r line; do
    log INFO "$label | $line"
  done
  local status=${PIPESTATUS[0]}
  set -e
  log INFO "Finished: $label exit_code=$status"
  return "$status"
}

run_shell_cmd() {
  local label="$1"
  local command="$2"
  log INFO "Starting: $label :: $command"
  set +e
  bash -lc "$command" 2>&1 | while IFS= read -r line; do
    log INFO "$label | $line"
  done
  local status=${PIPESTATUS[0]}
  set -e
  log INFO "Finished: $label exit_code=$status"
  return "$status"
}

cleanup_outputs() {
  log INFO "Cleaning stale output: $RESULTS_FILE and files inside $ANALYSIS_DIR"
  rm -f "$RESULTS_FILE"
  mkdir -p "$ANALYSIS_DIR"
  find "$ANALYSIS_DIR" -mindepth 1 -maxdepth 1 -type f -delete
}

wait_for_stable_file() {
  local file="$1"
  local poll_interval="$2"
  local stability_seconds="$3"
  local timeout="$4"
  local started now previous_size current_size stable_for

  started="$(date +%s)"
  previous_size=-1
  stable_for=0

  log INFO "Waiting for stable file: $file stability_seconds=$stability_seconds timeout=$timeout"

  while true; do
    now="$(date +%s)"
    if (( now - started > timeout )); then
      log ERROR "Timed out waiting for stable file: $file"
      return 1
    fi

    if [[ -f "$file" ]]; then
      current_size="$(stat -c '%s' "$file" 2>/dev/null || stat -f '%z' "$file")"
      if [[ "$current_size" -gt 0 && "$current_size" == "$previous_size" ]]; then
        stable_for=$((stable_for + poll_interval))
      else
        stable_for=0
        previous_size="$current_size"
      fi

      if (( stable_for >= stability_seconds )); then
        log INFO "File is stable: $file size=$current_size stable_for=${stable_for}s"
        return 0
      fi
    fi

    sleep "$poll_interval"
  done
}

watch_for_results_only() {
  log INFO "Watch mode enabled. Waiting for external scraper output."
  if command -v inotifywait >/dev/null 2>&1; then
    log INFO "inotifywait detected. Watching directory: $(dirname "$RESULTS_FILE")"
    while [[ ! -f "$RESULTS_FILE" ]]; do
      inotifywait -q -e create -e moved_to -e close_write "$(dirname "$RESULTS_FILE")" >/dev/null || true
    done
  fi
  wait_for_stable_file "$RESULTS_FILE" "$FILE_POLL_INTERVAL" "$STABILITY_SECONDS" "$WAIT_TIMEOUT"
}

run_pipeline() {
  cd "$PROJECT_ROOT"

  if [[ ! -f "$PATH_TO_ANALYZER" ]]; then
    log ERROR "Analyzer not found: $PATH_TO_ANALYZER"
    return 1
  fi

  run_shell_cmd "synchronize" "$SYNCHRONIZE_CMD"
  cleanup_outputs

  if [[ "${WATCH_ONLY:-0}" == "1" ]]; then
    watch_for_results_only
  else
    run_shell_cmd "scraper" "$SCRAPER_CMD"
    wait_for_stable_file "$RESULTS_FILE" "$FILE_POLL_INTERVAL" "$STABILITY_SECONDS" "$WAIT_TIMEOUT"
  fi

  run_cmd "analysis-default" "$PYTHON_BIN" "$PATH_TO_ANALYZER"
  run_cmd "analysis-suggestions-5" "$PYTHON_BIN" "$PATH_TO_ANALYZER" --suggestions-per-game 5
}

main() {
  log INFO "Pipeline requested project_root=$PROJECT_ROOT"
  exec 9>"$LOCK_FILE"
  log INFO "Waiting for exclusive pipeline lock: $LOCK_FILE"
  flock 9
  log INFO "Acquired exclusive pipeline lock"

  if run_pipeline; then
    log INFO "Pipeline completed successfully"
    exit 0
  else
    local status=$?
    log ERROR "Pipeline failed exit_code=$status"
    exit "$status"
  fi
}

main "$@"
