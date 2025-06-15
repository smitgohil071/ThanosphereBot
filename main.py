import logging
import requests
import pytz
from datetime import datetime
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, Dispatcher
)
from apscheduler.schedulers.background import BackgroundScheduler
from typing import Final, Dict

# Bot configuration
TELEGRAM_BOT_TOKEN: Final = "8165847651:AAFV2hSyWVy2pqcCm60yOisZU3Qs1w67e0E"
WEATHER_API_KEY: Final = "6b33fb715ddedc97349b1a50057cfa73"
BOT = Bot(token=TELEGRAM_BOT_TOKEN)

# Store user subscriptions for daily updates
user_subscriptions: Dict[int, str] = {}

# Flask App
app = Flask(__name__)

# Telegram Application & Dispatcher
telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
dp: Dispatcher = telegram_app

# Logging
logging.basicConfig(level=logging.INFO)


def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    data = response.json()
    main = data["main"]
    wind = data["wind"]
    sys = data["sys"]
    weather = data["weather"][0]

    # Convert to IST
    local_tz = pytz.timezone("Asia/Kolkata")
    sunrise = datetime.fromtimestamp(sys["sunrise"], pytz.UTC).astimezone(local_tz).strftime('%H:%M:%S')
    sunset = datetime.fromtimestamp(sys["sunset"], pytz.UTC).astimezone(local_tz).strftime('%H:%M:%S')

    return (
        f"📍 {data['name']}, {sys['country']}\n"
        f"🌡 Temp: {main['temp']}°C (Feels like {main['feels_like']}°C)\n"
        f"🔻 Min: {main['temp_min']}°C | 🔺 Max: {main['temp_max']}°C\n"
        f"💧 Humidity: {main['humidity']}%\n"
        f"🌬 Wind: {wind['speed']} m/s\n"
        f"🌅 Sunrise: {sunrise} IST | 🌇 Sunset: {sunset} IST\n"
        f"📋 Condition: {weather['main']} - {weather['description'].capitalize()}"
    )

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to Thanosphere Weather Bot!\nSend your city name to get current weather info.")

# Command: /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send a city name to get weather updates!\n/subscribe <city>\n/forecast <city>")

# Command: /subscribe
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /subscribe <city>")
        return
    city = " ".join(context.args)
    user_id = update.effective_user.id
    user_subscriptions[user_id] = city
    await update.message.reply_text(f"🔔 Subscribed to daily weather updates for {city}!")

# Command: /forecast
async def forecast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /forecast <city>")
        return
    city = " ".join(context.args)
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code != 200:
        await update.message.reply_text("❌ City not found.")
        return
    data = response.json()
    message = f"🌤 5-Day Forecast for {data['city']['name']}, {data['city']['country']}"
    for entry in data['list'][:5]:
        dt = datetime.fromtimestamp(entry['dt'], pytz.UTC).astimezone(pytz.timezone("Asia/Kolkata")).strftime('%a %H:%M')
        temp = entry['main']['temp']
        desc = entry['weather'][0]['description'].title()
        message += f"\n{dt}: {temp}°C - {desc}"
    await update.message.reply_text(message)

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    user_id = update.effective_user.id
    if user_id not in user_subscriptions:
        user_subscriptions[user_id] = city
    weather = get_weather(city)
    if weather:
        await update.message.reply_text(weather)
    else:
        await update.message.reply_text("❌ Couldn’t find that city. Try again.")

# Scheduler job
def scheduled_job():
    for user_id, city in user_subscriptions.items():
        weather = get_weather(city)
        if weather:
            try:
                BOT.send_message(chat_id=user_id, text=f"☀️ Daily Update:\n{weather}")
            except Exception as e:
                logging.error(f"Failed to send to {user_id}: {e}")

# Add handlers
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("help", help_command))
dp.add_handler(CommandHandler("subscribe", subscribe))
dp.add_handler(CommandHandler("forecast", forecast))
dp.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Run Flask server
@app.route("/")
def home():
    return "Thanosphere Weather Bot is Running!"

@app.route("/start-bot")
def start_bot():
    telegram_app.run_polling()
    return "Bot Started!"

# Start Flask + Scheduler
if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_job, "cron", hour=8, timezone="Asia/Kolkata")
    scheduler.start()

    app.run(host="0.0.0.0", port=8080)
