import logging
import asyncio
import pytz
from datetime import datetime
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# Set timezone to India
india_timezone = pytz.timezone("Asia/Kolkata")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# User city mapping
user_city_map = {}

# Get weather data
def get_weather(city: str) -> str:
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url).json()

        if response.get("cod") != 200:
            return "❌ City not found. Please enter a valid city name."

        data = response
        main = data['main']
        weather = data['weather'][0]
        wind = data['wind']
        sys = data['sys']

        sunrise = datetime.utcfromtimestamp(sys['sunrise']).replace(tzinfo=pytz.utc).astimezone(india_timezone).strftime('%I:%M %p')
        sunset = datetime.utcfromtimestamp(sys['sunset']).replace(tzinfo=pytz.utc).astimezone(india_timezone).strftime('%I:%M %p')

        return (
            f"📍 {data['name']}, {sys['country']}\n"
            f"🌡 Temp: {main['temp']}°C (Feels like {main['feels_like']}°C)\n"
            f"🔻 Min: {main['temp_min']}°C | 🔺 Max: {main['temp_max']}°C\n"
            f"💧 Humidity: {main['humidity']}%\n"
            f"🌬 Wind: {wind['speed']} m/s\n"
            f"🌤 Weather: {weather['description'].title()}\n"
            f"🌅 Sunrise: {sunrise} | 🌇 Sunset: {sunset}"
        )
    except Exception:
        return "⚠️ Sorry, couldn't fetch weather data right now."

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hello {user.first_name}, I’m ThanosphereBot 🌦\n\n"
        f"Just send me your city name to get the weather forecast!\n"
        f"You’ll also get daily updates at 8 AM IST."
    )

# Handle city name input
async def handle_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    city = update.message.text.strip()
    user_city_map[user_id] = city

    forecast = get_weather(city)
    await update.message.reply_text(forecast)

# Daily forecast job
async def daily_forecast(context: ContextTypes.DEFAULT_TYPE):
    for user_id, city in user_city_map.items():
        try:
            forecast = get_weather(city)
            await context.bot.send_message(chat_id=user_id, text=f"📅 Daily Forecast:\n{forecast}")
        except Exception:
            continue  # ignore failures silently

# Main entry
async def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city))

    # Schedule 8 AM daily update (Asia/Kolkata time)
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(daily_forecast, CronTrigger(hour=8, minute=0), args=[app.bot])
    scheduler.start()

    logger.info("✅ Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
