import asyncio
import logging
import sys
from os import getenv
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from motor.motor_asyncio import AsyncIOMotorClient

# Configure logging
logging.basicConfig(level=logging.INFO)

bot = Bot(token=getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# MongoDB configuration
client = AsyncIOMotorClient(getenv("MONGODB_URI"))
db = client["telegram_bot"]
users_collection = db["users"]

@dp.message(CommandStart())
async def start_command(message: types.Message):
    """Handle /start command and store user metadata"""
    try:
        user = message.from_user

        # Create user document
        user_data = {
            "user_id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "date_joined": datetime.now(),
            "is_bot": user.is_bot
        }

        # Check if user exists
        existing_user = await users_collection.find_one({"user_id": user.id})

        if not existing_user:
            # Insert new user
            await users_collection.insert_one(user_data)
            logging.info(f"New user registered: {user.id}")
            await message.reply(f"Welcome {user.first_name}! Your data has been stored.")
        else:
            await message.reply(f"Welcome back {user.first_name}! You're already registered.")

    except Exception as e:
        logging.error(f"Error processing /start command: {e}")
        await message.reply("An error occurred while processing your request.")

async def generate_help_text(dispatcher: Dispatcher):
    res = []
    commands = await bot.get_my_commands()
    for command in commands:
        res.push(f"/{command.command} - {command.description}")
    return "\n".join(res)

HELP_SECTIONS = {
    "general": """
📚 <b>General Help</b>
Basic bot usage information...
""",
    "faq": """
❓ <b>Frequently Asked Questions</b>
Q: Question 1?
A: Answer 1
"""
}

@dp.message(Command("help"))
async def help_menu(message: types.Message):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="General", callback_data="help_general")],
        [types.InlineKeyboardButton(text="Commands", callback_data="help_commands")],
        [types.InlineKeyboardButton(text="FAQ", callback_data="help_faq")]
    ])
    await message.answer("Select help section:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("help_"))
async def help_section(callback: types.CallbackQuery):
    section = callback.data.split("_")[1]

    answer = HELP_SECTIONS.get(section, "Section not found")
    if (section == "commands"):
        answer = await generate_help_text(dp)

    await callback.message.edit_text(
        answer,
        parse_mode="HTML",
        reply_markup=callback.message.reply_markup
    )
    await callback.answer()

@dp.message()
async def unknown_command(message: types.Message):
    await message.answer(
        "Sorry, I didn't understand that command. Try /help for assistance."
    )

async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls

    # And the run events dispatching
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
