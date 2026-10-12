#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-}" in
  start)
    shift
    exec uv run --no-project --offline "$script_dir/watch_controls.py" "$@"
    ;;
  stop)
    monitor_pid="${2:?需要当前观察进程的 PID}"
    [[ "$monitor_pid" =~ ^[1-9][0-9]*$ ]] || exit 2
    monitor_command="$(ps -p "$monitor_pid" -o args=)"
    [[ "$monitor_command" == *"$script_dir/watch_controls.py"* ]] || exit 2
    kill -TERM "$monitor_pid"
    ;;
  *)
    echo '用法：auto_gpt.sh start <watch_controls.py 参数> | stop <观察进程 PID>' >&2
    exit 2
    ;;
esac
