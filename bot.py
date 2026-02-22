from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import os
from dotenv import load_dotenv
from config.db import init_db
from services.UserService import UserService

init_db()
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am your bot. Please write your name to register.")

# Echo any text message
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = UserService.get_or_create_user(update.message.from_user.id, text, update.message.from_user.username)
    await update.message.reply_text(f"Hello {user.name}! You are registered.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run bot
    print("Bot is running...")
    app.run_polling()