#!/bin/bash

# Falhar em qualquer erro
set -e

# Verifica se o token foi passado
if [ -z "$GH_TOKEN" ]; then
  echo "❌ Variável GH_TOKEN não está definida. Exporte com: export GH_TOKEN=seu_token"
  exit 1
fi

echo "✅ Gerando nova versão com semantic-release..."
semantic-release version

echo "✅ Enviando commits e tags..."
git push origin main --follow-tags

echo "🚀 Publicando release no GitHub..."
semantic-release publish
