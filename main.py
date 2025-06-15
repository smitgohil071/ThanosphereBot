import logging
import os
import pytz
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# --- Setup logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Bot token and API key ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8165847651:AAFV2hSyWVy2pqcCm60yOisZU3Qs1w67e0E")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "6b33fb715ddedc97349b1a50057cfa73")

# --- User data storage ---
user_city_map = {}

# --- Weather fetching function ---
def fetch_weather(city):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    try:
        res = requests.get(url)
        data = res.json()
        if data.get("cod") != 200:
            return "City not found."

        main = data["main"]
        weather = data["weather"][0]
        sys = data["sys"]
        sunrise = datetime.utcfromtimestamp(sys["sunrise"] + 19800).strftime('%H:%M')
        sunset = datetime.utcfromtimestamp(sys["sunset"] + 19800).strftime('%H:%M')

        return (
            f"📍 {city.title()}, {data['sys']['country']}\n"
            f"🌡 Temp: {main['temp']}°C (Feels like {main['feels_like']}°C)\n"
            f"🔻 Min: {main['temp_min']}°C | 🔺 Max: {main['temp_max']}°C\n"
            f"🌥 {weather['main']} - {weather['description'].capitalize()}\n"
            f"🌅 Sunrise: {sunrise} IST\n"
            f"🌇 Sunset: {sunset} IST"
        )
    except Exception as e:
        logger.error(f"Weather fetch error: {e}")
        return "Couldn't retrieve weather data right now."

# --- Command handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"Hello {user.first_name}!\nSend your city name to get weather updates.")

async def handle_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    city = update.message.text.strip()
    user_city_map[user_id] = city
    weather = fetch_weather(city)
    await update.message.reply_text(weather)

# --- Scheduled weather updates ---
def scheduled_weather_job(app):
    for user_id, city in user_city_map.items():
        weather = fetch_weather(city)
        app.bot.send_message(chat_id=user_id, text=f"⏰ Daily Update:\n{weather}")

# --- Main application setup ---
async def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city))

    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: scheduled_weather_job(app), CronTrigger(hour=7, minute=30, timezone=pytz.timezone("Asia/Kolkata")))
    scheduler.start()

    logger.info("Bot started")
    await app.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
