#!/bin/bash

# Production Deployment Script for Accounting Office API
# This script helps deploy the application to production

set -e

echo "🚀 Starting Accounting Office API Deployment"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure your settings."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Run database migrations
echo "🗄️ Running database migrations..."
if command -v alembic &> /dev/null; then
    alembic upgrade head
else
    python -c "from database import init_database; init_database()"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs uploads

# Set proper permissions
echo "🔒 Setting permissions..."
chmod 755 .
chmod 644 *.py *.md *.txt
chmod 600 .env

# Run health check
echo "🏥 Running health check..."
python -c "
import asyncio
from main import app
from config import settings
print(f'✅ Configuration loaded: {settings.app_name} v{settings.app_version}')
print(f'✅ Database URL configured: {settings.database_url.split(\"://\")[0]}')
print('✅ Application ready for deployment')
"

echo "🎉 Deployment preparation complete!"
echo ""
echo "To start the application:"
echo "  Development: python main.py"
echo "  Production:  gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000"
echo "  Docker:      docker-compose up -d"
echo ""
echo "API Documentation: http://localhost:8000/docs"
echo "Health Check:      http://localhost:8000/api/health"