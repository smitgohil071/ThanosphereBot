import asyncio
import logging
import pytz
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Your bot token and weather API key
TELEGRAM_BOT_TOKEN = '8165847651:AAFV2hSyWVy2pqcCm60yOisZU3Qs1w67e0E'
WEATHER_API_KEY = '6b33fb715ddedc97349b1a50057cfa73'

# Logging for console
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Get weather data
def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code != 200:
        return None

    data = response.json()
    temp = data['main']['temp']
    feels_like = data['main']['feels_like']
    min_temp = data['main']['temp_min']
    max_temp = data['main']['temp_max']
    humidity = data['main']['humidity']
    wind = data['wind']['speed']
    sunrise_utc = datetime.utcfromtimestamp(data['sys']['sunrise'])
    sunset_utc = datetime.utcfromtimestamp(data['sys']['sunset'])

    ist = pytz.timezone('Asia/Kolkata')
    sunrise_ist = sunrise_utc.replace(tzinfo=pytz.utc).astimezone(ist).strftime('%H:%M:%S')
    sunset_ist = sunset_utc.replace(tzinfo=pytz.utc).astimezone(ist).strftime('%H:%M:%S')

    description = data['weather'][0]['description'].capitalize()
    city_name = data['name']
    country = data['sys']['country']

    return (
        f"📍 {city_name}, {country}\n"
        f"🌡 Temp: {temp}°C (Feels like {feels_like}°C)\n"
        f"🔻 Min: {min_temp}°C | 🔺 Max: {max_temp}°C\n"
        f"💧 Humidity: {humidity}%\n"
        f"🌬 Wind: {wind} m/s\n"
        f"🌅 Sunrise: {sunrise_ist} IST\n"
        f"🌇 Sunset: {sunset_ist} IST\n"
        f"📋 Condition: {description}"
    )

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌦 Welcome to *Thanosphere Weather Bot*!\n\n"
        "Send me your city name to get live weather updates instantly!",
        parse_mode='Markdown'
    )

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Just type your city name to get the latest weather info!")

# Handle city name text
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    weather = get_weather(city)
    if weather:
        await update.message.reply_text(weather)
    else:
        await update.message.reply_text("⚠️ Couldn't find weather for that city. Please try another.")

# Run bot
async def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Scheduler to send auto updates if needed
    scheduler = AsyncIOScheduler()
    scheduler.start()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot started...")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
