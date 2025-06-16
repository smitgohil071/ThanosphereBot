#!/bin/bash

echo "🔄 Starting Thanosphere Weather Bot..."

export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
export WEATHER_API_KEY="your_openweather_api_key"
export WEBHOOK_URL="https://your-app-name.onrender.com/webhook"

exec gunicorn thanossphere:flask_app --bind 0.0.0.0:$PORT
