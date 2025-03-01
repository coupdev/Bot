import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import random

TOKEN = "YOUR_BOT_TOKEN"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Стартовые деньги
start_balance = 500  # 500 виртуальных долларов на старте

# Словарь для хранения баланса пользователей
user_balance = {}

# Начальный коэффициент
multiplier = 0.1  # Начальный коэффициент (x0.1)

# Старт бота
@dp.message(CommandStart())
async def start_game(message: types.Message):
    user_id = message.from_user.id
    # Инициализируем баланс, если это первый запуск
    if user_id not in user_balance:
        user_balance[user_id] = start_balance

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💸 Тратить деньги на игру", callback_data="spend_money")]
        ]
    )
    await message.answer(f"Привет! У тебя есть {user_balance[user_id]} виртуальных долларов. Готов играть?", reply_markup=kb)

# Кнопка для выбора потратить деньги
@dp.callback_query(lambda c: c.data == "spend_money")
async def spend_money(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    kb = InlineKeyboardMarkup(row_width=2)
    for amount in [10, 50, 100, 200, 500]:  # Добавил 500$ как опцию
        kb.add(InlineKeyboardButton(text=f"Тратить {amount}$", callback_data=f"spend_{amount}"))
    await callback_query.message.answer("Выбери, сколько виртуальных долларов ты хочешь потратить на игру:", reply_markup=kb)

# Обработка выбора суммы для игры
@dp.callback_query(lambda c: c.data.startswith("spend_"))
async def play_game(callback_query: types.CallbackQuery):
    global multiplier  # Используем глобальную переменную multiplier
    user_id = callback_query.from_user.id
    amount_spent = int(callback_query.data.split("_")[1])

    if user_balance[user_id] < amount_spent:
        await callback_query.answer(f"У тебя недостаточно денег для игры. У тебя осталось {user_balance[user_id]}$.", show_alert=True)
        return

    # Обновляем баланс пользователя
    user_balance[user_id] -= amount_spent

    # Игровой процесс (случайное проигрывание или выигрыш с коэффициентом)
    game_result = random.choice(["win", "lose"])

    if game_result == "win":
        # Выигрыш: ставка умножается на текущий коэффициент
        winnings = amount_spent * multiplier
        user_balance[user_id] += winnings

        # Увеличиваем коэффициент случайным образом в диапазоне от 0.1 до 1000.0
        multiplier = random.uniform(0.1, 1000.0)  # Коэффициент теперь случайное число от 0.1 до 1000.0

        await callback_query.message.answer(f"Поздравляем, ты выиграл! Твой коэффициент: x{multiplier:.2f}. Твой баланс: {user_balance[user_id]}$")
    else:
        # Проигрыш: вся ставка сгорает, коэффициент сбрасывается на 0.1
        multiplier = 0.1
        await callback_query.message.answer(f"Ты проиграл. Вся ставка сгорела. Твой коэффициент сброшен на x{multiplier}. Твой баланс: {user_balance[user_id]}$")

if __name__ == "__main__":
    import asyncio
    from aiogram import executor
    logging.basicConfig(level=logging.INFO)
    asyncio.run(dp.start_polling(bot))
