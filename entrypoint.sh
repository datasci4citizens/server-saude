#!/bin/sh

echo "Rodando migrations..."
python manage.py makemigrations --noinput
python manage.py migrate

echo "Populando tabelas"
python manage.py seed_concepts

echo "📥 Rodando inserts SQL diretos"
python manage.py dbshell < /app/scripts/data.sql || echo "⚠️ Erro ao rodar data.sql (talvez já existam os dados)"

# Criação automática do superusuário
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "👤 Criando superusuário (se necessário)..."
  python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username="$DJANGO_SUPERUSER_USERNAME").exists():
    User.objects.create_superuser(
        username="$DJANGO_SUPERUSER_USERNAME",
        email="$DJANGO_SUPERUSER_EMAIL",
        password="$DJANGO_SUPERUSER_PASSWORD"
    )
EOF
else
  echo "Variáveis de superusuário não definidas. Pulando criação."
fi

# Criação automática do SocialApp do Google
if [ "$VITE_GOOGLE_CLIENT_ID" ] && [ "$VITE_GOOGLE_CLIENT_SECRET" ]; then
  echo "Configurando SocialApp do Google (se necessário)..."
  python manage.py shell <<EOF
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

site_id = int("$SOCIALAPP_SITE_ID" or 1)
site, _ = Site.objects.get_or_create(id=site_id, defaults={"domain": "localhost", "name": "localhost"})

if not SocialApp.objects.filter(provider="google").exists():
    app = SocialApp.objects.create(
        provider="google",
        name="Google",
        client_id="$VITE_GOOGLE_CLIENT_ID",
        secret="$VITE_GOOGLE_CLIENT_SECRET"
    )
    app.sites.add(site)
    print("SocialApp criado.")
else:
    print("ℹSocialApp já existe.")
EOF
else
  echo "VITE_GOOGLE_CLIENT_ID ou VITE_GOOGLE_CLIENT_SECRET não definidos. Ignorando SocialApp."
fi

echo "Iniciando servidor Django..."
exec "$@"
