from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from telegram.ext import ApplicationBuilder
import requests
import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from typing import Final, Dict
import os
import asyncio

# ==== Config ====
TOKEN: Final = "8165847651:AAFV2hSyWVy2pqcCm60yOisZU3Qs1w67e0E"
WEATHER_API_KEY: Final = "6b33fb715ddedc97349b1a50057cfa73"
URL: Final = "https://thanosspherebot.onrender.com"  # Replace with your real Render URL

# ==== Flask App ====
flask_app = Flask(__name__)

# ==== Bot State ====
user_subscriptions: Dict[int, str] = {}
application: Application = None

# ==== Weather Function ====
def get_weather(city: str) -> str:
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

# ==== Handlers ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send your city name to get weather updates!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start - Start\n/subscribe <city> - Daily update")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /subscribe <city>")
        return
    city = " ".join(context.args)
    user_id = update.effective_user.id
    user_subscriptions[user_id] = city
    await update.message.reply_text(f"🔔 Subscribed to daily weather for {city}!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    user_id = update.effective_user.id
    user_subscriptions[user_id] = city
    weather = get_weather(city)
    if weather:
        await update.message.reply_text(weather)
    else:
        await update.message.reply_text("❌ City not found.")

# ==== Daily Task ====
scheduler = BackgroundScheduler()

def send_daily():
    if application:
        for uid, city in user_subscriptions.items():
            report = get_weather(city)
            if report:
                asyncio.run(application.bot.send_message(uid, f"☀️ Daily Weather:\n{report}"))

scheduler.add_job(send_daily, "cron", hour=8, timezone="Asia/Kolkata")
scheduler.start()

# ==== Flask Routes ====
@flask_app.route('/')
def home():
    return "Thanosphere Weather Bot is alive!"

@flask_app.route(f'/{TOKEN}', methods=['POST'])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return 'OK'

# ==== Run ====
async def main():
    global application
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await application.bot.set_webhook(f"{URL}/{TOKEN}")
    print("✅ Webhook set!")

if __name__ == '__main__':
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
    flask_app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
