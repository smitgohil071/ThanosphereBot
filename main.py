import threading
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import pytz
import datetime

# 🔐 Keys — ensure these are set via env vars or hardcoded here
TELEGRAM_BOT_TOKEN = "8165847651:AAFV2hSyWVy2pqcCm60yOisZU3Qs1w67e0E"
WEATHER_API_KEY = "6b33fb715ddedc97349b1a50057cfa73"

# Store daily-subscription preferences
user_subscriptions = {}

# —————— Flask app ——————
app = Flask(__name__)

@app.route("/", methods=["GET", "HEAD"])
def index():
    return "Bot is running!", 200

# —————— Telegram handlers ——————
def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    res = requests.get(url)
    if res.status_code != 200:
        return None
    d = res.json()
    main = d["main"]; wind = d["wind"]; sys = d["sys"]; w = d["weather"][0]
    tz = pytz.timezone("Asia/Kolkata")
    sunrise = datetime.datetime.fromtimestamp(sys["sunrise"], pytz.UTC).astimezone(tz).strftime("%H:%M:%S")
    sunset = datetime.datetime.fromtimestamp(sys["sunset"], pytz.UTC).astimezone(tz).strftime("%H:%M:%S")
    return (
        f"📍 {d['name']}, {sys['country']}\n"
        f"🌡 Temp: {main['temp']}°C (Feels like {main['feels_like']}°C)\n"
        f"🔻 Min: {main['temp_min']}°C | 🔺 Max: {main['temp_max']}°C\n"
        f"💧 Humidity: {main['humidity']}%\n"
        f"🌬 Wind: {wind['speed']} m/s\n"
        f"🌅 Sunrise: {sunrise} | 🌇 Sunset: {sunset}\n"
        f"📋 Condition: {w['main']} - {w['description'].title()}"
    )

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌦 Welcome! Send a city name to get weather.")

async def subscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /subscribe <city>")
        return
    city = " ".join(ctx.args)
    user_subscriptions[update.effective_user.id] = city
    await update.message.reply_text(f"✅ Subscribed to daily updates for {city}")

async def help_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start\n/subscribe <city>")

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    report = get_weather(update.message.text.strip())
    if report:
        await update.message.reply_text(report)
        user_subscriptions[update.effective_user.id] = update.message.text.strip()
    else:
        await update.message.reply_text("❌ Couldn't find that city.")

# —————— Scheduler ——————
def send_daily():
    for uid, city in user_subscriptions.items():
        rpt = get_weather(city)
        if rpt:
            try:
                app_bot.bot.send_message(chat_id=uid, text=f"☀️ Daily Update:\n{rpt}")
            except:
                pass

sched = BackgroundScheduler()
sched.add_job(send_daily, "cron", hour=8, timezone="Asia/Kolkata")
sched.start()

# —————— Telegram bot runner ——————
def run_bot():
    global app_bot
    app_bot = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("subscribe", subscribe))
    app_bot.add_handler(CommandHandler("help", help_command))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app_bot.run_polling()

# —————— Start both ——————
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)
