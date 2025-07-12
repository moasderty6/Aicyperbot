import json
import re
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.executor import start_webhook
import openai
import aiohttp

API_TOKEN = os.getenv('BOT_TOKEN')  # استيراد التوكن من متغير بيئة
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CHANNEL_USERNAME = "p2p_LRN"

WEBHOOK_HOST = os.getenv('WEBHOOK_HOST')  # مثل https://yourdomain.com
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
    except Exception:
        return False

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    subscribed = await is_subscribed(message.from_user.id)
    if not subscribed:
        keyboard = InlineKeyboardMarkup(row_width=1)
        join_button = InlineKeyboardButton(text="اشترك في القناة أولاً", url=f"https://t.me/{CHANNEL_USERNAME}")
        keyboard.add(join_button)
        await message.reply(
            "مرحبًا! يجب عليك الاشتراك في قناة @p2p_LRN لاستخدام هذا البوت.\n"
            "اضغط على الزر أدناه للاشتراك ثم أعد إرسال /start.",
            reply_markup=keyboard
        )
        return

    text = (
        "مرحبًا! أنا بوت الأمن السيبراني الذكي.\n"
        "اسألني أي سؤال في الأمن السيبراني وسأجيبك مع تقديم مصادر تعليمية مفيدة.\n\n"
        "يمكنك أيضًا استخدام الأمر /sources لعرض جميع المصادر المتاحة."
    )
    await message.reply(text)

@dp.message_handler(commands=['sources'])
async def send_sources_list(message: types.Message):
    subscribed = await is_subscribed(message.from_user.id)
    if not subscribed:
        keyboard = InlineKeyboardMarkup(row_width=1)
        join_button = InlineKeyboardButton(text="اشترك في القناة أولاً", url=f"https://t.me/{CHANNEL_USERNAME}")
        keyboard.add(join_button)
        await message.reply(
            "عذرًا، يجب عليك الاشتراك في قناة @p2p_LRN لاستخدام هذا البوت.\n"
            "اضغط على الزر للاشتراك ثم أعد إرسال /sources.",
            reply_markup=keyboard
        )
        return

    reply_text = "📚 *قائمة المصادر التعليمية المتاحة:* \n\n"
    for topic, sources in sources_db.items():
        reply_text += f"🔹 *{topic}:*\n"
        for src in sources:
            reply_text += f" - [{src['title']}]({src['url']})\n"
        reply_text += "\n"
    await message.reply(reply_text, parse_mode='Markdown')

@dp.message_handler()
async def handle_question(message: types.Message):
    subscribed = await is_subscribed(message.from_user.id)
    if not subscribed:
        keyboard = InlineKeyboardMarkup(row_width=1)
        join_button = InlineKeyboardButton(text="اشترك في القناة أولاً", url=f"https://t.me/{CHANNEL_USERNAME}")
        keyboard.add(join_button)
        await message.reply(
            "عذرًا، يجب عليك الاشتراك في قناة @p2p_LRN لاستخدام هذا البوت.\n"
            "اضغط على الزر للاشتراك ثم أعد إرسال رسالتك.",
            reply_markup=keyboard
        )
        return

    user_question = message.text.strip()
    topic = find_topic(user_question)

    prompt = f"أجب على هذا السؤال في الأمن السيبراني بشكل تعليمي وأخلاقي وباختصار: {user_question}"

    try:
        response = await openai.Completion.acreate(
            engine="gpt-4o-mini",
            prompt=prompt,
            max_tokens=500,
            temperature=0.7,
        )
        answer = response.choices[0].text.strip()
    except Exception as e:
        await message.reply(f"حدث خطأ في الاتصال بـ OpenAI: {e}")
        return

    reply_text = f"💡 *الإجابة:*\n{answer}\n"

    if topic:
        sources = get_sources(topic)
        if sources:
            reply_text += "\n📚 *مصادر تعليمية مفيدة:* \n"
            for src in sources:
                reply_text += f"- [{src['title']}]({src['url']})\n"

    await message.reply(reply_text, parse_mode='Markdown')

async def on_startup(dispatcher):
    await bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook set to {WEBHOOK_URL}")

async def on_shutdown(dispatcher):
    await bot.delete_webhook()
    print("Webhook deleted")

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
