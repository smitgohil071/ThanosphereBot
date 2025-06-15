from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from apscheduler.schedulers.background import BackgroundScheduler
import requests, datetime, pytz
from typing import Final, Dict

# ------------------ CONFIG -------------------
TELEGRAM_BOT_TOKEN: Final = "8165847651:AAFV2hSyWVy2pqcCm60yOisZU3Qs1w67e0E"
WEATHER_API_KEY: Final = "6b33fb715ddedc97349b1a50057cfa73"
user_subscriptions: Dict[int, str] = {}

# Flask app
app = Flask(__name__)
telegram_app = None  # will hold Application object

# ---------------- WEATHER --------------------
def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    res = requests.get(url)
    if res.status_code != 200:
        return None
    data = res.json()
    weather = data["weather"][0]
    main = data["main"]
    sys = data["sys"]
    wind = data["wind"]

    tz = pytz.timezone("Asia/Kolkata")
    sunrise = datetime.datetime.fromtimestamp(sys["sunrise"], pytz.UTC).astimezone(tz).strftime("%H:%M:%S")
    sunset = datetime.datetime.fromtimestamp(sys["sunset"], pytz.UTC).astimezone(tz).strftime("%H:%M:%S")

    return (
        f"📍 {data['name']}, {sys['country']}\n"
        f"🌡 Temp: {main['temp']}°C (Feels like {main['feels_like']}°C)\n"
        f"🔻 Min: {main['temp_min']}°C | 🔺 Max: {main['temp_max']}°C\n"
        f"💧 Humidity: {main['humidity']}%\n"
        f"🌬 Wind: {wind['speed']} m/s\n"
        f"🌅 Sunrise: {sunrise} | 🌇 Sunset: {sunset}\n"
        f"🌫 Visibility: {data.get('visibility', 0)/1000} km\n"
        f"🌀 Condition: {weather['main']} - {weather['description'].title()}"
    )

# --------------- HANDLERS ---------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to Thanosphere Weather Bot! Send me a city name.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start\n/help\n/subscribe <city>\n/forecast <city>")

async def forecast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /forecast <city>")
        return
    city = " ".join(context.args)
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={WEATHER_API_KEY}&units=metric"
    res = requests.get(url)
    if res.status_code != 200:
        await update.message.reply_text("❌ City not found.")
        return
    data = res.json()
    message = f"🌦️ Forecast for {data['city']['name']}:\n"
    for item in data['list'][:5]:
        dt = datetime.datetime.fromtimestamp(item['dt'], pytz.UTC).astimezone(pytz.timezone("Asia/Kolkata")).strftime('%a %H:%M')
        temp = item['main']['temp']
        desc = item['weather'][0]['description'].title()
        message += f"{dt}: {temp}°C - {desc}\n"
    await update.message.reply_text(message)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /subscribe <city>")
        return
    city = " ".join(context.args)
    user_subscriptions[update.effective_user.id] = city
    await update.message.reply_text(f"✅ Subscribed to daily updates for {city}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    if city.lower() in ["hi", "hello", "hey"]:
        await update.message.reply_text("Hey! 👋 Send a city name to get weather.")
        return
    report = get_weather(city)
    if report:
        await update.message.reply_text(report)
        user_subscriptions[update.effective_user.id] = city
    else:
        await update.message.reply_text("❌ City not found.")

# ------------- SCHEDULED JOB -----------------
def send_daily_weather():
    for user_id, city in user_subscriptions.items():
        report = get_weather(city)
        if report:
            try:
                telegram_app.bot.send_message(chat_id=user_id, text=f"☀️ Daily Weather:\n{report}")
            except:
                pass

scheduler = BackgroundScheduler()
scheduler.add_job(send_daily_weather, "cron", hour=8, timezone="Asia/Kolkata")
scheduler.start()

# -------------- TELEGRAM INIT ----------------
def run_telegram():
    global telegram_app
    telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("forecast", forecast))
    telegram_app.add_handler(CommandHandler("subscribe", subscribe))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    telegram_app.run_polling()

# ------------------ FLASK --------------------
@app.route("/")
def home():
    return "ThanosphereBot is Running!"

if __name__ == "__main__":
    Thread(target=run_telegram).start()
    app.run(host="0.0.0.0", port=10000)
