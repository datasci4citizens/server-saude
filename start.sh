#!/bin/bash
chmod +x entrypoint.sh

./entrypoint.sh

if [ -z "$PORT" ]; then
  echo "Rodando localmente com runserver..."
  python manage.py runserver 0.0.0.0:8000
else
  echo "Rodando no Render com Gunicorn..."
  exec gunicorn citizens_project.wsgi:application --bind 0.0.0.0:$PORT
fi
