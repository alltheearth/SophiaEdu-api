#!/bin/bash
set -e

echo "🔄 Aguardando banco de dados..."
python manage.py wait_for_db || sleep 5

echo "🔄 Executando migrações..."
python manage.py migrate --noinput

echo "🔄 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "✅ Iniciando servidor..."
exec "$@"
