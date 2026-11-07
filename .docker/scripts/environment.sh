#!/bin/sh
set -e

DB_TARGET_HOST="${DB_HOST:-db}"
DB_TARGET_PORT="${DB_PORT:-5432}"

REDIS_TARGET_HOST="${REDIS_HOST:-redis}"
REDIS_TARGET_PORT="${REDIS_PORT:-6379}"

echo "Aguardando o PostgreSQL em ${DB_TARGET_HOST}:${DB_TARGET_PORT}..."
while ! python -c "import socket; s = socket.socket(); s.settimeout(1); s.connect(('${DB_TARGET_HOST}', int('${DB_TARGET_PORT}'))); s.close()" 2>/dev/null; do
  sleep 1
done
echo "PostgreSQL conectado com sucesso!"

echo "Aguardando o Redis em ${REDIS_TARGET_HOST}:${REDIS_TARGET_PORT}..."
while ! python -c "import socket; s = socket.socket(); s.settimeout(1); s.connect(('${REDIS_TARGET_HOST}', int('${REDIS_TARGET_PORT}'))); s.close()" 2>/dev/null; do
  sleep 1
done
echo "Redis conectado com sucesso!"

# Aplica migrações apenas na API
if [ "$1" = "python" ] && [ "$2" = "manage.py" ] && [ "$3" = "runserver" ]; then
    echo "Aplicando migrações do banco de dados..."
    python manage.py migrate --noinput
fi

exec "$@"