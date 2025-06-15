from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)
import datetime
import requests
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from typing import Final, Dict
import os
import asyncio

# ==== Configuration ====
BOT_TOKEN: Final = "8165847651:AAFV2hSyWVy2pqcCm60yOisZU3Qs1w67e0E"
WEATHER_API_KEY: Final = "6b33fb715ddedc97349b1a50057cfa73"
RENDER_EXTERNAL_URL: Final = "https://your-app-name.onrender.com"  # 🔁 Replace this with your real Render URL
WEBHOOK_PATH: Final = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL: Final = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

PORT = int(os.environ.get("PORT", 10000))
user_subscriptions: Dict[int, str] = {}

# ==== Flask App ====
app = Flask(__name__)
telegram_app: Application = ApplicationBuilder().token(BOT_TOKEN).build()

# ==== Weather Logic ====
def get_weather(city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        res = requests.get(url)
        if res.status_code != 200:
            return None
        data = res.json()
        main = data["main"]
        weather = data["weather"][0]
        wind = data["wind"]
        sys = data["sys"]

        sunrise = datetime.datetime.fromtimestamp(sys["sunrise"], pytz.UTC).astimezone(
            pytz.timezone("Asia/Kolkata")).strftime('%H:%M:%S')
        sunset = datetime.datetime.fromtimestamp(sys["sunset"], pytz.UTC).astimezone(
            pytz.timezone("Asia/Kolkata")).strftime('%H:%M:%S')

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
    except:
        return None

# ==== Telegram Command Handlers ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Send a city name or use /subscribe <city> to get daily weather ☀️")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Start\n"
        "/subscribe <city> - Daily updates\n"
        "/help - Show help"
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /subscribe <city>")
        return
    city = " ".join(context.args)
    user_id = update.effective_user.id
    user_subscriptions[user_id] = city
    await update.message.reply_text(f"🔔 Subscribed to daily updates for {city}.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    user_id = update.effective_user.id
    user_subscriptions[user_id] = city
    report = get_weather(city)
    if report:
        await update.message.reply_text(report)
    else:
        await update.message.reply_text("❌ Couldn't find that city.")

# ==== Daily Weather Update Scheduler ====
scheduler = BackgroundScheduler()

def send_daily_updates():
    for user_id, city in user_subscriptions.items():
        report = get_weather(city)
        if report:
            asyncio.run(telegram_app.bot.send_message(chat_id=user_id, text=f"☀️ Daily Weather:\n{report}"))

scheduler.add_job(send_daily_updates, "cron", hour=8, timezone="Asia/Kolkata")
scheduler.start()

# ==== Flask Webhook Route ====
@app.route(WEBHOOK_PATH, methods=["POST"])
async def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    await telegram_app.process_update(update)
    return "OK"

@app.route("/", methods=["GET"])
def root():
    return "✅ Thanosphere Bot is LIVE with Webhook!"

# ==== Launch ====
async def main():
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("subscribe", subscribe))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await telegram_app.bot.set_webhook(WEBHOOK_URL)
    print("🔗 Webhook set!")

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
    app.run(host="0.0.0.0", port=PORT)
