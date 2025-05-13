import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from openai import OpenAI
from uuid import uuid4
from dotenv import load_dotenv  

# Логгинг
logging.basicConfig(level=logging.INFO)

# Загрузка .env файла
load_dotenv()  # ДОБАВЛЕНО

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")  # ИЗМЕНЕНО
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # ИЗМЕНЕНО

# Инициализация
openai_client = OpenAI(api_key=OPENAI_API_KEY)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

# Функция исправления текста
async def correct_text(prompt: str) -> str:
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты корректор. Исправь грамматические ошибки и правильно расставь знаки препинания."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Ошибка OpenAI: {e}")
        return "Произошла ошибка при обработке текста."

# Inline-запрос
@router.inline_query()
async def handle_inline_query(inline_query: InlineQuery):
    query = inline_query.query.strip()
    if not query:
        return

    corrected = await correct_text(query)

    result = InlineQueryResultArticle(
        id=str(uuid4()),
        title="Исправленный текст",
        input_message_content=InputTextMessageContent(
            message_text=corrected
        ),
        description=corrected[:50] + "..." if len(corrected) > 50 else corrected
    )

    await bot.answer_inline_query(inline_query.id, results=[result], cache_time=0)

# Подключение и запуск
dp.include_router(router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
