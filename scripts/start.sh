#!/usr/bin/env bash
# 启动本地 PostgreSQL（解压版）+ Django API + Vite 前端。
# 全部监听 127.0.0.1，仅保存匿名合成数据。
set -euo pipefail

ROOT="/workspace"
PG_BIN="$ROOT/.pgsql/root/usr/lib/postgresql/15/bin"
PGDATA="$ROOT/.pgsql/data"
PGLOG="$ROOT/.pgsql/log/pg.log"
VENV="$ROOT/.venv/bin/python"

mkdir -p "$ROOT/.pgsql/log"

if ! "$PG_BIN/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
  echo "[1/3] 启动 PostgreSQL (127.0.0.1:55432) ..."
  "$PG_BIN/pg_ctl" -D "$PGDATA" -l "$PGLOG" -w start
else
  echo "[1/3] PostgreSQL 已在运行"
fi

echo "[2/3] 启动 Django REST API (127.0.0.1:8000) ..."
cd "$ROOT/backend"
if ! curl -sf http://127.0.0.1:8000/api/elections/ >/dev/null 2>&1; then
  nohup "$VENV" manage.py runserver 127.0.0.1:8000 \
    > "$ROOT/.pgsql/log/django.log" 2>&1 &
  echo $! > "$ROOT/.pgsql/django.pid"
  sleep 2
fi

echo "[3/3] 启动 Vite 前端 (127.0.0.1:5173) ..."
cd "$ROOT/frontend"
if ! curl -sf http://127.0.0.1:5173/ >/dev/null 2>&1; then
  nohup npm run dev -- --host 127.0.0.1 \
    > "$ROOT/.pgsql/log/vite.log" 2>&1 &
  echo $! > "$ROOT/.pgsql/vite.pid"
fi

cat <<EOF

全部就绪：
  前端页面 : http://127.0.0.1:5173/
  API 列表 : http://127.0.0.1:8000/api/elections/
  管理后台 : http://127.0.0.1:8000/admin/  (python manage.py createsuperuser 建账号)

停止服务：bash $ROOT/scripts/stop.sh
EOF
