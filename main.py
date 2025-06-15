# flask_weather_bot/main.py

from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
import requests
import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from typing import Final, Dict
import threading
import os

# ==== Configuration ====
TELEGRAM_BOT_TOKEN: Final = "8165847651:AAFV2hSyWVy2pqcCm60yOisZU3Qs1w67e0E"
WEATHER_API_KEY: Final = "6b33fb715ddedc97349b1a50057cfa73"
PORT = int(os.environ.get("PORT", 10000))

# ==== Flask App ====
flask_app = Flask(__name__)

# ==== Weather Bot State ====
user_subscriptions: Dict[int, str] = {}

# ==== Bot Functions ====
def log_message(update: Update):
    user = update.effective_user
    username = user.username or user.first_name or "UnknownUser"
    chat_type = update.effective_chat.type
    message_text = update.message.text.strip()
    chat_label = "PRIVATE" if chat_type == "private" else "GROUP"
    print(f"[{chat_label}] @{username}: {message_text}")

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

    local_tz = pytz.timezone("Asia/Kolkata")
    sunrise = datetime.datetime.fromtimestamp(sys["sunrise"], pytz.UTC).astimezone(local_tz).strftime('%H:%M:%S')
    sunset = datetime.datetime.fromtimestamp(sys["sunset"], pytz.UTC).astimezone(local_tz).strftime('%H:%M:%S')

    return (
        f"📍 {data['name']}, {sys['country']}\n"
        f"🌡 Temp: {main['temp']}°C (Feels like {main['feels_like']}°C)\n"
        f"🔻 Min: {main['temp_min']}°C | 🔺 Max: {main['temp_max']}°C\n"
        f"💧 Humidity: {main['humidity']}%\n"
        f"🌬 Wind: {wind['speed']} m/s\n"
        f"🌅 Sunrise: {sunrise} | 🌇 Sunset: {sunset}\n"
        f"🌁 Visibility: {data.get('visibility', 0) / 1000} km\n"
        f"🌀 Condition: {weather['main']} - {weather['description'].title()}"
    )

# ==== Command Handlers ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message(update)
    await update.message.reply_text("Welcome! Send me your city name and I'll give you weather updates every day ☀️")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message(update)
    await update.message.reply_text("/start - Start the bot\n/subscribe <city> - Daily updates\nOr send a city name anytime!")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message(update)
    if not context.args:
        await update.message.reply_text("Usage: /subscribe <city>")
        return
    city = " ".join(context.args)
    user_id = update.effective_user.id
    user_subscriptions[user_id] = city
    await update.message.reply_text(f"🔔 Subscribed to daily updates for {city}.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message(update)
    city = update.message.text.strip()
    user_id = update.effective_user.id
    if user_id not in user_subscriptions:
        user_subscriptions[user_id] = city
    report = get_weather(city)
    if report:
        await update.message.reply_text(report)
    else:
        await update.message.reply_text("❌ Couldn't find that city.")

# ==== Daily Weather Task ====
scheduler = BackgroundScheduler()

def scheduled_weather():
    for user_id, city in user_subscriptions.items():
        report = get_weather(city)
        if report:
            try:
                telegram_app.bot.send_message(chat_id=user_id, text=f"☀️ Daily Weather Update:\n{report}")
            except Exception:
                pass

scheduler.add_job(scheduled_weather, "cron", hour=8, timezone="Asia/Kolkata")
scheduler.start()

# ==== Start Telegram Bot in Thread ====
def run_bot():
    global telegram_app
    telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("subscribe", subscribe))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Telegram Bot is running...")
    telegram_app.run_polling()

bot_thread = threading.Thread(target=run_bot)
bot_thread.start()

# ==== Flask Route to Keep Render Alive ====
@flask_app.route('/')
def home():
    return "Thanosphere Weather Bot is Live!"

if __name__ == '__main__':
    flask_app.run(host="0.0.0.0", port=PORT)
