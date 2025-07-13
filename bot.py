import os
import json
import aiohttp
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# إعداد البوت
API_TOKEN = "ضع توكن البوت هنا"
GROQ_API_KEY = "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"
WEBHOOK_HOST = "https://yourrenderurl.onrender.com"  # عدّل هذا حسب رابط مشروعك
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 3000))
CHANNEL_USERNAME = "p2p_LRN"

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)
session: aiohttp.ClientSession = None

# تحميل المصادر
with open('sources.json', encoding='utf-8') as f:
    sources_db = json.load(f)

# كلمات مفتاحية لتحديد المجال
keywords_map = {
    "اختراق": "الاختراق الأخلاقي",
    "تشفير": "التشفير",
    "هندسة اجتماعية": "الهندسة الاجتماعية",
    "فيروس": "البرمجيات الخبيثة",
    "برمجة آمنة": "البرمجة الآمنة",
    "malware": "البرمجيات الخبيثة"
}

def find_topic(text: str):
    text = text.lower()
    for keyword, topic in keywords_map.items():
        if keyword in text:
            return topic
    return None

async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status != "left"
    except:
        return False

@router.message(Command("start"))
async def cmd_start(msg: types.Message):
    if not await is_subscribed(msg.from_user.id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="اشترك في القناة 🔒", url=f"https://t.me/{CHANNEL_USERNAME}")]
        ])
        await msg.answer("🔒 يجب الاشتراك في القناة لاستخدام البوت.", reply_markup=keyboard)
        return
    await msg.answer("👋 أهلًا بك! أرسل سؤالك في الأمن السيبراني وسأجيبك باستخدام الذكاء الاصطناعي.\n\nاستخدم /sources لمطالعة المصادر.")

@router.message(Command("sources"))
async def cmd_sources(msg: types.Message):
    if not await is_subscribed(msg.from_user.id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="اشترك في القناة 🔒", url=f"https://t.me/{CHANNEL_USERNAME}")]
        ])
        await msg.answer("🔒 يجب الاشتراك في القناة لاستخدام هذه الميزة.", reply_markup=keyboard)
        return

    response = "📚 *المصادر المتاحة:*\n\n"
    for topic, links in sources_db.items():
        response += f"🔹 *{topic}*\n"
        for item in links:
            response += f"- [{item['title']}]({item['url']})\n"
        response += "\n"
    await msg.answer(response)

@router.message()
async def handle_question(msg: types.Message):
    global session
    if not await is_subscribed(msg.from_user.id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="اشترك في القناة 🔒", url=f"https://t.me/{CHANNEL_USERNAME}")]
        ])
        await msg.answer("🔒 يجب الاشتراك في القناة لاستخدام البوت.", reply_markup=keyboard)
        return

    waiting_message = await msg.answer("⏳ *يتم الآن توليد أفضل إجابة لك...*\nالرجاء الانتظار لحظات.", parse_mode="Markdown")

    question = msg.text.strip()
    topic = find_topic(question)

    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "qwen/qwen3-32b",
            "messages": [{"role": "user", "content": f"أجب بشكل تعليمي ومفصل عن: {question}"}],
            "temperature": 0.7,
            "max_tokens": 2048
        }

        async with session.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload) as resp:
            data = await resp.json()

            if "choices" not in data:
                raise Exception(data)

            answer = data["choices"][0]["message"]["content"]

            response = f"💡 *الإجابة:*\n{answer.strip()}\n\n"
            if topic and topic in sources_db:
                response += "📚 *مصادر مفيدة:*\n"
                for item in sources_db[topic]:
                    response += f"- [{item['title']}]({item['url']})\n"

            await waiting_message.edit_text(response)

    except Exception as e:
        await waiting_message.edit_text(f"❌ حدث خطأ أثناء الاتصال بـ Groq:\n`{e}`", parse_mode="Markdown")

async def on_shutdown(app: web.Application):
    global session
    if session:
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
    site = web.TCPSite(runner, host=WEBAPP_HOST, port=WEBAPP_PORT)
    await site.start()

    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook يعمل على: {WEBHOOK_URL}")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
