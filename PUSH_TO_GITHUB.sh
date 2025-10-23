#!/bin/bash

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║   📤 SUBIENDO ARCHIVOS A GITHUB                                     ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Verificar que estamos en la carpeta correcta
if [ ! -f "barber_api_production.py" ]; then
    echo "❌ Error: No estás en la carpeta barbershop-backend"
    echo "   Ejecuta: cd /Users/sebastianlaborde/barbershop-website/barbershop-backend"
    exit 1
fi

echo "✅ Carpeta correcta detectada"
echo ""

# Verificar archivos importantes
echo "📋 Verificando archivos..."
if [ -f "runtime.txt" ]; then
    echo "✅ runtime.txt existe"
    echo "   Contenido: $(cat runtime.txt)"
else
    echo "⚠️  runtime.txt no existe, creándolo..."
    echo "python-3.11.0" > runtime.txt
    echo "✅ runtime.txt creado"
fi

if [ -f "barber_api_production.py" ]; then
    echo "✅ barber_api_production.py existe"
fi

if [ -f "requirements.txt" ]; then
    echo "✅ requirements.txt existe"
fi

if [ -f "render.yaml" ]; then
    echo "✅ render.yaml existe"
fi

echo ""
echo "📦 Agregando archivos a git..."
git add .

echo ""
echo "💾 Haciendo commit..."
git commit -m "Fix Python version to 3.11.0"

echo ""
echo "📤 Subiendo a GitHub..."
echo "⚠️  Te pedirá tus credenciales:"
echo "   Username: tu_usuario_de_github"
echo "   Password: tu_personal_access_token"
echo ""

git push

echo ""
echo "✅ ¡Listo! Archivos subidos a GitHub"
echo ""
echo "🔄 Ahora ve a Render y haz:"
echo "   1. Click 'Manual Deploy'"
echo "   2. Selecciona 'Clear build cache & deploy'"
echo "   3. Espera 5-7 minutos"
echo ""

