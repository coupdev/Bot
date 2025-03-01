import asyncio
import random
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

TOKEN = ""
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

FAKE_PAYMENT_LINK = "t.me/send?start=IVDRMGlTT9No"

# Хранилище состояния игрока
class GameState(StatesGroup):
    waiting_for_payment = State()
    playing = State()

# Хранилище множителя
active_games = {}

# Команда старт (начало игры)
@dp.message(CommandStart())
async def start_game(message: types.Message, state: FSMContext):
    await state.set_state(GameState.waiting_for_payment)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Оплатить", url=FAKE_PAYMENT_LINK)]]
    )
    await message.answer("Оплати счет, чтобы начать игру!", reply_markup=kb)

# Подтверждение оплаты (старт игры)
@dp.message(lambda msg: msg.text.lower() == "я оплатил")
async def confirm_payment(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in active_games:
        await message.answer("Игра уже запущена!")
        return

    await state.set_state(GameState.playing)
    active_games[user_id] = {"multiplier": 1.0, "running": True}

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🛑 Стоп", callback_data="stop_game")]]
    )
    await message.answer("Игра началась! Чем дольше ждешь, тем выше множитель!", reply_markup=kb)

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
    active_games[user_id]["running"] = False
    await callback.message.answer(f"Вы остановились вовремя! Ваш выигрыш умножен на x{multiplier:.2f} 🎉")
    active_games.pop(user_id, None)

# Обработка кнопки "Начать сначала"
@dp.callback_query(lambda c: c.data == "restart_game")
async def restart_game(callback: types.CallbackQuery, state: FSMContext):
    await start_game(callback.message, state)

# Запуск бота
async def main():
    await dp.start_polling(bot)

if name == "__main__":
    asyncio.run(main())