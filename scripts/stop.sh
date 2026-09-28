#!/usr/bin/env bash
# 停止本项目启动的 Django / Vite / PostgreSQL。
set -euo pipefail

ROOT="/workspace"
PG_BIN="$ROOT/.pgsql/root/usr/lib/postgresql/15/bin"

for name in django vite; do
  pidfile="$ROOT/.pgsql/$name.pid"
  if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    kill "$(cat "$pidfile")" 2>/dev/null || true
    rm -f "$pidfile"
    echo "已停止 $name"
  fi
done

# 兜底：清理可能游离的 runserver / vite 进程
pkill -f "manage.py runserver 127.0.0.1:8000" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

"$PG_BIN/pg_ctl" -D "$ROOT/.pgsql/data" stop >/dev/null 2>&1 || true
echo "PostgreSQL 已停止"
