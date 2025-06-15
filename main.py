import logging
import requests
import asyncio
from pytz import timezone
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Constants
TELEGRAM_BOT_TOKEN = '8165847651:AAFV2hSyWVy2pqcCm60yOisZU3Qs1w67e0E'
WEATHER_API_KEY = '6b33fb715ddedc97349b1a50057cfa73'
DEFAULT_TIMEZONE = timezone('Asia/Kolkata')

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global storage for user cities
user_cities = {}

# Weather fetcher
def get_weather(city: str) -> str:
    url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric'
    try:
        res = requests.get(url).json()

        if res.get("cod") != 200:
            return f"❌ Could not find weather for '{city}'. Please try again."

        temp = res['main']['temp']
        feels_like = res['main']['feels_like']
        temp_min = res['main']['temp_min']
        temp_max = res['main']['temp_max']
        humidity = res['main']['humidity']
        pressure = res['main']['pressure']
        wind = res['wind']['speed']
        condition = res['weather'][0]['description'].title()

        # Convert sunrise/sunset to IST
        sunrise = datetime.fromtimestamp(res['sys']['sunrise'], tz=DEFAULT_TIMEZONE).strftime('%I:%M %p')
        sunset = datetime.fromtimestamp(res['sys']['sunset'], tz=DEFAULT_TIMEZONE).strftime('%I:%M %p')

        return (f"📍 *{res['name']}, {res['sys']['country']}*\n"
                f"🌡 *{temp}°C* (Feels like {feels_like}°C)\n"
                f"🔻 Min: {temp_min}°C | 🔺 Max: {temp_max}°C\n"
                f"💧 Humidity: {humidity}% | 🔵 Pressure: {pressure} hPa\n"
                f"💨 Wind: {wind} m/s | ☁️ Condition: {condition}\n"
                f"🌅 Sunrise: {sunrise} | 🌇 Sunset: {sunset}")
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return "⚠️ Could not retrieve weather. Please try again later."

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"👋 Hello {user.first_name}! Send me a city name and I'll give you the weather updates!")

async def handle_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    city = update.message.text.strip()

    user_cities[chat_id] = city
    weather_info = get_weather(city)
    await update.message.reply_markdown(weather_info)

async def daily_weather(context: ContextTypes.DEFAULT_TYPE):
    for chat_id, city in user_cities.items():
        weather_info = get_weather(city)
        try:
            await context.bot.send_message(chat_id=chat_id, text=weather_info, parse_mode='Markdown')
        except Exception as e:
            logger.warning(f"Failed to send message to {chat_id}: {e}")

async def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city))

    # Daily job scheduler
    scheduler = AsyncIOScheduler(timezone=DEFAULT_TIMEZONE)
    scheduler.add_job(daily_weather, 'cron', hour=7, minute=0, args=[app.bot])
    scheduler.start()

    print("✅ Bot started.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
