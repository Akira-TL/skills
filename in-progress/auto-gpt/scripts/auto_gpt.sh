#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-}" in
  monitor)
    shift
    exec uv run --no-project --offline "$script_dir/monitor_session.py" "$@"
    ;;
  start)
    shift
    exec uv run --no-project --offline "$script_dir/watch_controls.py" "$@"
    ;;
  read|continue)
    operation="$1"
    shift
    exec uv run --no-project --offline "$script_dir/reply_once.py" "$operation" "$@"
    ;;
  stop)
    monitor_pid="${2:?需要当前观察进程的 PID}"
    [[ "$monitor_pid" =~ ^[1-9][0-9]*$ ]] || exit 2
    monitor_command="$(ps -p "$monitor_pid" -o args=)"
    [[ "$monitor_command" == *"$script_dir/watch_controls.py"* || "$monitor_command" == *"$script_dir/monitor_session.py"* ]] || exit 2
    kill -TERM "$monitor_pid"
    ;;
  *)
    echo '用法：auto_gpt.sh monitor <观察参数> | start <兼容观察参数> | read|continue <单次动作参数> | stop <观察进程 PID>' >&2
    exit 2
    ;;
esac
