import json
import re
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.executor import start_webhook
import openai
import aiohttp
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv('BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CHANNEL_USERNAME = "p2p_LRN"

WEBHOOK_HOST = os.getenv('WEBHOOK_HOST')
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = int(os.getenv('PORT', 3000))

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
openai.api_key = OPENAI_API_KEY

with open('sources.json', encoding='utf-8') as f:
    sources_db = json.load(f)

keywords_map = {
    "اختراق": "الاختراق الأخلاقي",
    "penetration": "الاختراق الأخلاقي",
    "هاكر": "الاختراق الأخلاقي",
    "اختبار": "الاختراق الأخلاقي",
    "برمجة آمنة": "البرمجة الآمنة",
    "secure coding": "البرمجة الآمنة",
    "تشفير": "التشفير",
    "cryptography": "التشفير",
    "هندسة اجتماعية": "الهندسة الاجتماعية",
    "social engineering": "الهندسة الاجتماعية",
    "فيروس": "البرمجيات الخبيثة",
    "malware": "البرمجيات الخبيثة",
    "فيروسات": "البرمجيات الخبيثة",
    "keylogger": "البرمجيات الخبيثة",
}

def find_topic(question: str):
    question_lower = question.lower()
    for key, topic in keywords_map.items():
        if re.search(r'\b' + re.escape(key) + r'\b', question_lower):
            return topic
    return None

def get_sources(topic: str):
    return sources_db.get(topic, [])

async def is_subscribed(user_id: int):
    try:
        member = await bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        return member.status != 'left'
    except:
        return False

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("اشترك في القناة", url=f"https://t.me/{CHANNEL_USERNAME}"))
        await message.reply("يرجى الاشتراك في القناة لاستخدام البوت.", reply_markup=keyboard)
        return

    await message.reply("مرحبًا! اسألني أي سؤال عن الأمن السيبراني وسأجيبك مع مصادر تعليمية.")

@dp.message_handler(commands=['sources'])
async def send_sources_list(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("اشترك في القناة", url=f"https://t.me/{CHANNEL_USERNAME}"))
        await message.reply("يرجى الاشتراك في القناة لاستخدام هذه الميزة.", reply_markup=keyboard)
        return

    text = "📚 *قائمة المصادر المتاحة:*\n\n"
    for topic, sources in sources_db.items():
        text += f"🔹 *{topic}*\n"
        for src in sources:
            text += f" - [{src['title']}]({src['url']})\n"
        text += "\n"
    await message.reply(text, parse_mode="Markdown")

@dp.message_handler()
async def handle_question(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("اشترك في القناة", url=f"https://t.me/{CHANNEL_USERNAME}"))
        await message.reply("اشترك أولاً لمتابعة استخدام البوت.", reply_markup=keyboard)
        return

    question = message.text.strip()
    topic = find_topic(question)
    prompt = f"أجب بشكل تعليمي ومبسط عن: {question}"

    try:
        response = await openai.Completion.acreate(
            engine="gpt-4o",
            prompt=prompt,
            max_tokens=500,
            temperature=0.7,
        )
        answer = response.choices[0].text.strip()
    except Exception as e:
        answer = f"حدث خطأ: {e}"

    final = f"🔐 *الإجابة:*\n{answer}\n\n"
    if topic:
        final += "📚 *مصادر إضافية:*\n"
        for src in get_sources(topic):
            final += f" - [{src['title']}]({src['url']})\n"

    await message.reply(final, parse_mode="Markdown")

async def on_startup(dispatcher):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dispatcher):
    await bot.delete_webhook()

if __name__ == '__main__':
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
