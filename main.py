# thanossphere.py

from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)
import requests, datetime, pytz, os, asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from typing import Final, Dict

# ==== Configuration ====
TELEGRAM_BOT_TOKEN: Final = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
WEATHER_API_KEY: Final = os.getenv("WEATHER_API_KEY", "YOUR_WEATHER_API_KEY")
WEBHOOK_URL: Final = os.getenv("WEBHOOK_URL", "https://your-app-name.onrender.com/webhook")
PORT = int(os.environ.get("PORT", 10000))

flask_app = Flask(__name__)
user_subscriptions: Dict[int, str] = {}

# ==== Weather Function ====
def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    data = response.json()
    main, wind, sys = data["main"], data["wind"], data["sys"]
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

# ==== Bot Handlers ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌤 Welcome! Send your city name or use /subscribe <city> for daily updates.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start - Welcome message\n/subscribe <city> - Daily updates\nSend a city anytime.")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /subscribe <city>")
        return
    city = " ".join(context.args)
    user_subscriptions[update.effective_user.id] = city
    await update.message.reply_text(f"🔔 Subscribed to daily updates for {city}.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    user_subscriptions[update.effective_user.id] = city
    report = get_weather(city)
    await update.message.reply_text(report or "❌ Couldn't find that city.")

# ==== Telegram Application ====
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("subscribe", subscribe))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ==== Scheduler for Daily Weather ====
def scheduled_weather():
    for user_id, city in user_subscriptions.items():
        report = get_weather(city)
        if report:
            try:
                application.bot.send_message(chat_id=user_id, text=f"🌤 Daily Weather Update:\n{report}")
            except Exception as e:
                print(f"❌ Error sending to {user_id}: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_weather, "cron", hour=8, timezone="Asia/Kolkata")
scheduler.start()

# ==== Flask Routes ====
@flask_app.route('/')
def index():
    return "🌐 Thanosphere Weather Bot is Live!"

@flask_app.route('/webhook', methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "OK"

# ==== Start App ====
if __name__ == '__main__':
    async def run():
        await application.bot.set_webhook(url=WEBHOOK_URL)
        print("✅ Webhook set successfully.")

    asyncio.run(run())
    flask_app.run(host="0.0.0.0", port=PORT)
