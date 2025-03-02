import asyncio
import random
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.default import DefaultBotProperties

TOKEN = "TOKEN"
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Хранилище состояния игрока
class GameState(StatesGroup):
    waiting_for_choice = State()  # Ожидание выбора суммы для игры
    playing = State()

# Хранилище активных игр
active_games = {}

# Хранилище баланса пользователей
user_balances = {}

# Команда старт (начало игры)
@dp.message(CommandStart())
async def start_game(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    # Начисляем 500$
    if user_id not in user_balances:
        user_balances[user_id] = 500

    await state.set_state(GameState.waiting_for_choice)

    # Кнопки выбора суммы для игры (добавлены 10 и 50 долларов)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="10$", callback_data="play_10")],
            [InlineKeyboardButton(text="50$", callback_data="play_50")],
            [InlineKeyboardButton(text="100$", callback_data="play_100")],
            [InlineKeyboardButton(text="200$", callback_data="play_200")],
            [InlineKeyboardButton(text="500$", callback_data="play_500")]
        ]
    )

    await message.answer(
        f"Привет, {message.from_user.first_name}! У тебя есть {user_balances[user_id]}$. Выбери сумму для игры.",
        reply_markup=kb
    )

# Обработка выбора суммы для игры
@dp.callback_query(lambda c: c.data.startswith("play_"))
async def play_game(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in user_balances or user_balances[user_id] <= 0:
        await callback.answer("У тебя недостаточно денег для игры!", show_alert=True)
        return

    selected_amount = int(callback.data.split("_")[1])
    if user_balances[user_id] < selected_amount:
        await callback.answer("У тебя недостаточно средств для этой игры!", show_alert=True)
        return

    # Начинаем игру
    user_balances[user_id] -= selected_amount
    await state.set_state(GameState.playing)
    active_games[user_id] = {"multiplier": 1.0, "running": True, "bet": selected_amount}

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🛑 Стоп", callback_data="stop_game")]]
    )
    await callback.message.answer(
        f"Игра началась! Ты поставил {selected_amount}$. Чем дольше ждешь, тем выше множитель!",
        reply_markup=kb
    )

    await run_game(user_id)

# Логика роста множителя
async def run_game(user_id: int):
    while user_id in active_games and active_games[user_id]["running"]:
        await asyncio.sleep(random.uniform(0.5, 1.5))  # Разные интервалы роста
        if user_id not in active_games:  
            break
        active_games[user_id]["multiplier"] += round(random.uniform(0.1, 0.5), 2)
        await bot.send_message(user_id, f"Текущий множитель: x{active_games[user_id]['multiplier']:.2f}")

        if random.random() < 0.05:  # 5% шанс на авто-краш
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔄 Начать сначала", callback_data="restart_game")]]
            )
            await bot.send_message(user_id, "❌ Машинка разбилась! Вы проиграли всю сумму.", reply_markup=kb)
            active_games.pop(user_id, None)
            break

# Обработка нажатия кнопки "Стоп"
@dp.callback_query(lambda c: c.data == "stop_game")
async def stop_game(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in active_games or not active_games[user_id]["running"]:
        await callback.answer("Игра уже закончена!", show_alert=True)
        return

    multiplier = active_games[user_id]["multiplier"]
    bet = active_games[user_id]["bet"]
    win = bet * multiplier
    active_games[user_id]["running"] = False
    await callback.message.answer(f"Вы остановились вовремя! Ваш выигрыш: {win:.2f}$ 🎉")
    user_balances[user_id] += int(win)  # Добавляем выигрыш на баланс
    active_games.pop(user_id, None)

# Обработка кнопки "Начать сначала"
@dp.callback_query(lambda c: c.data == "restart_game")
async def restart_game(callback: types.CallbackQuery, state: FSMContext):
    await start_game(callback.message, state)

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        
    
