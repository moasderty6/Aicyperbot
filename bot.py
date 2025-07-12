import os
import asyncio
import json
import aiohttp
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from dotenv import load_dotenv
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# تحميل .env
load_dotenv()

# إعداد المتغيرات
API_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHANNEL_USERNAME = "p2p_LRN"
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")  # مثال: https://yourapp.onrender.com
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 3000))

# البوت
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# جلسة aiohttp واحدة على مستوى التطبيق
session: aiohttp.ClientSession = None

# المصادر
with open('sources.json', encoding='utf-8') as f:
    sources_db = json.load(f)

# تحليل الكلمات
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
    "keylogger": "البرمجيات الخبيثة"
}

def find_topic(text: str):
    text = text.lower()
    for keyword, topic in keywords_map.items():
        if keyword in text:
            return topic
    return None

async def is_subscribed(user_id: int):
    try:
        member = await bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status != "left"
    except:
        return False

@router.message(Command(commands=["start", "help"]))
async def start_handler(msg: types.Message):
    if not await is_subscribed(msg.from_user.id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="اشترك في القناة", url=f"https://t.me/{CHANNEL_USERNAME}")]
        ])
        await msg.answer("يرجى الاشتراك في القناة أولاً لاستخدام البوت.", reply_markup=keyboard)
        return
    await msg.answer("👋 مرحبًا! اسألني أي شيء في الأمن السيبراني وسأجيبك + أرسل لك مصادر مفيدة.\n\nاستخدم /sources لعرض المصادر الكاملة.")

@router.message(Command(commands=["sources"]))
async def show_sources(msg: types.Message):
    if not await is_subscribed(msg.from_user.id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="اشترك في القناة", url=f"https://t.me/{CHANNEL_USERNAME}")]
        ])
        await msg.answer("يرجى الاشتراك في القناة لاستخدام هذه الميزة.", reply_markup=keyboard)
        return

    response = "📚 *المصادر المتاحة:*\n\n"
    for topic, srcs in sources_db.items():
        response += f"🔹 *{topic}*\n"
        for s in srcs:
            response += f"- [{s['title']}]({s['url']})\n"
        response += "\n"
    await msg.answer(response)

@router.message()
async def answer_question(msg: types.Message):
    if not await is_subscribed(msg.from_user.id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="اشترك في القناة", url=f"https://t.me/{CHANNEL_USERNAME}")]
        ])
        await msg.answer("يرجى الاشتراك في القناة أولاً لاستخدام البوت.", reply_markup=keyboard)
        return

    question = msg.text.strip()
    topic = find_topic(question)

    try:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": f"أجب بشكل تعليمي عن: {question}"}],
            "temperature": 0.7
        }
        async with session.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload) as resp:
            data = await resp.json()
            answer = data["choices"][0]["message"]["content"]

            response = f"💡 *الإجابة:*\n{answer.strip()}\n\n"
            if topic and topic in sources_db:
                response += "📚 *مصادر مفيدة:*\n"
                for s in sources_db[topic]:
                    response += f"- [{s['title']}]({s['url']})\n"

            await msg.answer(response)

    except Exception as e:
        await msg.answer(f"❌ حدث خطأ أثناء الاتصال بـ OpenAI:\n`{e}`")

async def on_shutdown(app: web.Application):
    await session.close()
    await bot.session.close()

async def main():
    global session
    session = aiohttp.ClientSession()

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot, webhook_path=WEBHOOK_PATH).register(app, WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    app.on_shutdown.append(on_shutdown)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEBAPP_HOST, WEBAPP_PORT)
    await site.start()

    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook شغال على: {WEBHOOK_URL}")

if __name__ == "__main__":
    asyncio.run(main())
