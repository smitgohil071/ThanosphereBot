from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import requests
import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from typing import Final, Dict

# Developer Info
author = "Smit Gohil"
botname = "Thanosphere Weather Bot"
version = "1.0.2"

# API Keys
TELEGRAM_BOT_TOKEN: Final = "8165847651:AAFV2hSyWVy2pqcCm60yOisZU3Qs1w67e0E"
WEATHER_API_KEY: Final = "6b33fb715ddedc97349b1a50057cfa73"
GEMINI_API_KEY: Final = "AIzaSyDlN2UBt6i8-uhJkSbL0XEKyU9IhKmZOoU"

user_subscriptions: Dict[int, str] = {}

# Logging

def log_message(update: Update):
    user = update.effective_user
    username = user.username or user.first_name or "UnknownUser"
    chat_type = update.effective_chat.type
    message_text = update.message.text.strip()
    chat_label = "PRIVATE" if chat_type == "private" else "GROUP"
    print(f"[{chat_label}] @{username}: {message_text}")

# Get weather data
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
    sunrise = datetime.datetime.fromtimestamp(sys["sunrise"], pytz.UTC).astimezone(local_tz).strftime('%H:%M:%S')
    sunset = datetime.datetime.fromtimestamp(sys["sunset"], pytz.UTC).astimezone(local_tz).strftime('%H:%M:%S')

    report = (
        f"\U0001F4CD {data['name']}, {sys['country']}\n"
        f"\U0001F321 Temp: {main['temp']}\u00B0C (Feels like {main['feels_like']}\u00B0C)\n"
        f"\U0001F53B Min: {main['temp_min']}\u00B0C | \U0001F53A Max: {main['temp_max']}\u00B0C\n"
        f"\U0001F4A7 Humidity: {main['humidity']}%\n"
        f"\U0001F32C Wind: {wind['speed']} m/s\n"
        f"\U0001F305 Sunrise: {sunrise} | \U0001F307 Sunset: {sunset}\n"
        f"\U0001F301 Visibility: {data.get('visibility', 0) / 1000} km\n"
        f"\U0001F300 Condition: {weather['main']} - {weather['description'].title()}"
    )
    if weather['main'].lower() == "thunderstorm":
        report += "\n\U0001F4A5 Thanos declares: 'I am inevitable!' Brace for the storm!"
    return report

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message(update)
    user_id = update.effective_user.id
    if user_id not in user_subscriptions:
        await update.message.reply_text("Welcome! Send me your city name and I'll give you weather updates every day ☀️")

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message(update)
    await update.message.reply_text(
        "/start - Start the bot\n"
        "/forecast <city> - 5-day forecast\n"
        "/subscribe <city> - Get daily updates\n"
        "Or send a city name anytime!"
    )

# /forecast
async def forecast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message(update)
    if not context.args:
        await update.message.reply_text("Please provide a city name. Example: /forecast Mumbai")
        return
    city = " ".join(context.args)
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code != 200:
        await update.message.reply_text("❌ City not found.")
        return
    data = response.json()
    message = f"🌩️ 5-Day Forecast for {data['city']['name']}, {data['city']['country']}\n"
    for entry in data['list'][:5]:
        dt = datetime.datetime.fromtimestamp(entry['dt'], pytz.UTC).astimezone(pytz.timezone("Asia/Kolkata")).strftime('%a %H:%M')
        temp = entry['main']['temp']
        desc = entry['weather'][0]['description'].title()
        message += f"\n{dt}: {temp}\u00B0C - {desc}"
    await update.message.reply_text(message)

# /subscribe
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message(update)
    if not context.args:
        await update.message.reply_text("Usage: /subscribe <city>")
        return
    city = " ".join(context.args)
    user_id = update.effective_user.id
    user_subscriptions[user_id] = city
    await update.message.reply_text(f"🔔 Subscribed to daily weather updates for {city}.")

# Daily update task
scheduler = BackgroundScheduler()

def scheduled_weather():
    for user_id, city in user_subscriptions.items():
        report = get_weather(city)
        if report:
            try:
                app.bot.send_message(chat_id=user_id, text=f"☀️ Daily Weather Update:\n{report}")
            except Exception:
                pass

scheduler.add_job(scheduled_weather, "cron", hour=8, timezone="Asia/Kolkata")
scheduler.start()

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_message(update)
    city = update.message.text.strip()
    if city.lower() in ["hi", "hello", "hey"]:
        await update.message.reply_text("Hey! Send me a city name to get the weather ☁️")
        return
    user_id = update.effective_user.id
    if user_id not in user_subscriptions:
        user_subscriptions[user_id] = city  # Auto-subscribe
    report = get_weather(city)
    if report:
        await update.message.reply_text(report)
    else:
        await update.message.reply_text("❌ Couldn’t find that city.")

# Run bot
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("forecast", forecast))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("⚡ Weather bot is running...")
    app.run_polling()
