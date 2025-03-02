import asyncio
import json
import os
import random
import hashlib

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    BotCommand,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent
)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")  # Make sure your .env file has BOT_TOKEN=your_token

# File paths
BALANCES_FILE = "user_balances.json"
STATS_FILE = "user_stats.json"

# Global variables
user_balances = {}
user_stats = {}

# FSM (Finite State Machine) classes
class BetState(StatesGroup):
    entering_bet = State()

class VivodState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_username = State()

# Storage functions
def load_balances():
    global user_balances
    if os.path.exists(BALANCES_FILE):
        try:
            with open(BALANCES_FILE, 'r', encoding='utf-8') as f:
                user_balances = {int(k): v for k, v in json.load(f).items()}
        except Exception as e:
            print(f"Error loading balances: {e}")
            user_balances = {}
    else:
        user_balances = {}

def save_balances():
    try:
        with open(BALANCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_balances, f)
    except Exception as e:
        print(f"Error saving balances: {e}")

def load_stats():
    global user_stats
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                user_stats = json.load(f)
        except Exception as e:
            print(f"Error loading stats: {e}")
    else:
        user_stats = {}

def save_stats():
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(user_stats, f)
    except Exception as e:
        print(f"Error saving stats: {e}")

def increment_games_played(user_id):
    str_user_id = str(user_id)
    if str_user_id not in user_stats:
        user_stats[str_user_id] = {"games_played": 0}
    
    user_stats[str_user_id]["games_played"] = user_stats[str_user_id].get("games_played", 0) + 1
    save_stats()

# Game class
class ActiveGame:
    def __init__(self, bet: int):
        self.bet = bet
        self.multiplier = 1.0
        self.running = True

active_games = {}

# Create routers
start_router = Router()
balance_router = Router()
top_router = Router()
game_router = Router()
profile_router = Router()
vivod_router = Router()

# Start router handlers
@start_router.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Initialize user balance if they don't have one
    if user_id not in user_balances:
        user_balances[user_id] = 500
        save_balances()

    # Create buttons for bets
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="10$", callback_data="play_10")],
            [InlineKeyboardButton(text="50$", callback_data="play_50")],
            [InlineKeyboardButton(text="100$", callback_data="play_100")],
            [InlineKeyboardButton(text="200$", callback_data="play_200")],
            [InlineKeyboardButton(text="500$", callback_data="play_500")],
            [InlineKeyboardButton(text="💰 Ввести свою сумму", callback_data="enter_bet")]
        ]
    )

    # Send message with bet options
    await message.answer(
        f"Привет, {message.from_user.first_name}! У тебя {user_balances[user_id]}$. Выбери сумму для игры.",
        reply_markup=kb
    )

@start_router.callback_query(lambda c: c.data.startswith("play_"))
async def handle_bet(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    bet = int(callback.data.split("_")[1])  # Extract bet from callback_data

    # Check if user has enough balance
    if user_balances.get(user_id, 0) < bet:
        await callback.message.answer("У тебя недостаточно средств для этой ставки.")
        return

    # Subtract bet from user balance
    user_balances[user_id] -= bet
    save_balances()

    # Create a new game for the user
    active_games[user_id] = ActiveGame(bet)
    
    # Start the game
    x = await callback.message.answer(f"Игра началась! Ставка {bet}$.")
    await run_game(user_id, x)

@start_router.callback_query(lambda c: c.data == "enter_bet")
async def ask_for_bet(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BetState.entering_bet)
    await callback.message.answer("Введите сумму ставки (числом):")
    await callback.answer()

@start_router.message(BetState.entering_bet)
async def process_custom_bet(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        # Преобразуем текст в число
        bet = int(message.text)
        if bet <= 0:
            raise ValueError("Ставка должна быть положительным числом.")
        if user_balances.get(user_id, 0) < bet:  # Проверяем баланс
            await message.answer("Недостаточно средств! Введите сумму заново:")
            return
    except ValueError:
        await message.answer("Неверный формат ставки! Введите число:")
        return

    # Вычитаем ставку из баланса пользователя
    user_balances[user_id] -= bet
    save_balances()

    # Создаем новую игру для пользователя
    active_games[user_id] = ActiveGame(bet)
    
    # Запускаем игру
    x = await message.answer(f"Игра началась! Ставка {bet}$.")
    await run_game(user_id, x)  # Убедитесь, что функция run_game определена

    await state.clear()  # Сбрасываем состояние после ввода ставки
    
# Balance router handlers
@balance_router.message(Command("balance"))
async def show_balance(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 500
        save_balances()
    
    await message.answer(f"Ваш текущий баланс: {user_balances[user_id]}$")

async def get_top_players_text(limit=10):
    if not user_balances:
        return "Пока нет игроков в списке!"
    
    # Сортируем пользователей по балансу и берем топ
    top_users = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    top_message = "🏆 <b>Топ игроков:</b>\n\n"
    
    for i, (user_id, balance) in enumerate(top_users, 1):
        try:
            # Получаем информацию о пользователе
            user_info = await bot.get_chat(user_id)
            username = user_info.username or user_info.first_name or f"Игрок #id{user_id}"
            top_message += f"{i}. {username} — {balance}$\n"
        except Exception:
            # Если информацию о пользователе получить не удалось
            top_message += f"{i}. Игрок #id{user_id} — {balance}$\n"
    
    return top_message

    
@top_router.message(Command("top"))
async def show_top_players(message: types.Message):
    top_message = await get_top_players_text()
    await message.answer(top_message)

# Обработчик inline-запросов
@top_router.inline_query()
async def inline_query_handler(inline_query: InlineQuery):
    # Проверяем, что запрос соответствует команде top
    if inline_query.query.lower() in ['top', 'топ', 'лидеры', 'leaders']:
        top_text = await get_top_players_text()
        
        # Создаем ID для результата (хеш от текста + текущего времени)
        result_id = hashlib.md5(f"{top_text}_{inline_query.id}".encode()).hexdigest()
        
        # Создаем inline-результат
        results = [
            InlineQueryResultArticle(
                id=result_id,
                title="Топ игроков 🏆",
                description="Показать список лидеров по балансу",
                input_message_content=InputTextMessageContent(
                    message_text=top_text,
                    parse_mode=ParseMode.HTML
                ),
                thumb_url="https://cdn-icons-png.flaticon.com/512/4489/4489871.png",
                thumb_width=48,
                thumb_height=48
            )
        ]
        
        # Отправляем результат
        await inline_query.answer(results=results, cache_time=30)
    else:
        # Для других запросов показываем подсказку
        result_id = hashlib.md5(f"help_{inline_query.id}".encode()).hexdigest()
        
        results = [
            InlineQueryResultArticle(
                id=result_id,
                title="Доступные команды",
                description="Введите 'top' для просмотра списка лидеров",
                input_message_content=InputTextMessageContent(
                    message_text="<b>Доступные inline-команды:</b>\n• <code>top</code> - Показать топ игроков",
                    parse_mode=ParseMode.HTML
                )
            )
        ]
        
        await inline_query.answer(results=results, cache_time=300)

# Game router handlers
@game_router.message(Command("game"))
async def start_game(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id not in user_balances:
        user_balances[user_id] = 500
        save_balances()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="10$", callback_data="play_10")],
            [InlineKeyboardButton(text="50$", callback_data="play_50")],
            [InlineKeyboardButton(text="100$", callback_data="play_100")],
            [InlineKeyboardButton(text="200$", callback_data="play_200")],
            [InlineKeyboardButton(text="500$", callback_data="play_500")],
            [InlineKeyboardButton(text="💰 Ввести свою сумму", callback_data="enter_bet")]
        ]
    )

    await message.answer(
        f"Привет, {message.from_user.first_name}! У тебя {user_balances[user_id]}$. Выбери сумму для игры.",
        reply_markup=kb
    )

async def run_game(user_id: int, message: types.Message):
    # Increment games played counter
    increment_games_played(user_id)
    
    while active_games[user_id].running:
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        if user_id not in active_games:
            break
        
        active_games[user_id].multiplier += round(random.uniform(0.1, 0.5), 2)
        
        try:
            await message.edit_text(
                f"Текущий множитель: x{active_games[user_id].multiplier:.2f}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="🛑 Стоп", callback_data="stop_game")]]
                )
            )
        except Exception:
            pass

        if random.random() < 0.05:
            await message.edit_text("❌ Машинка разбилась! Вы проиграли всю сумму.")
            active_games.pop(user_id, None)
            save_balances()
            break

@game_router.callback_query(lambda c: c.data == "stop_game")
async def stop_game(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id in active_games:
        game = active_games[user_id]
        game.running = False
        
        # Calculate winnings
        winnings = int(game.bet * game.multiplier)
        user_balances[user_id] += winnings
        save_balances()
        
        # Remove game from active games
        active_games.pop(user_id)
        
        await callback.message.edit_text(
            f"🎮 Игра завершена!\n"
            f"💰 Ставка: {game.bet}$\n"
            f"✖️ Множитель: x{game.multiplier:.2f}\n"
            f"💵 Выигрыш: {winnings}$"
        )

# Profile router handlers
@profile_router.message(Command("profile"))
async def show_profile(message: types.Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username

    # Ensure user has a balance
    if user_id not in user_balances:
        user_balances[user_id] = 500
        save_balances()
    
    balance = user_balances[user_id]
    
    # Get games played from stats
    str_user_id = str(user_id)
    games_played = user_stats.get(str_user_id, {}).get("games_played", 0)

    profile_text = (
        f"👤 <b>Профиль</b>\n"
        f"🆔 <b>ID:</b> {user_id}\n"
        f"📛 <b>Имя:</b> {first_name}\n"
        f"🔗 <b>Юзернейм:</b> @{username if username else 'Нет'}\n"
        f"💰 <b>Баланс:</b> {balance}$\n"
        f"🎮 <b>Сыграно игр:</b> {games_played}"
    )

    await message.answer(profile_text)

# Vivod (withdrawal) router handlers

@vivod_router.message(Command("vivod"))
async def start_vivod(message: types.Message, state: FSMContext):
    await message.answer("Введите сумму, которую хотите вывести:")
    await state.set_state(VivodState.waiting_for_amount)

@vivod_router.message(Command("cancel"))
async def cancel_vivod(message: types.Message, state: FSMContext):
    # Проверяем, находится ли пользователь в процессе вывода
    current_state = await state.get_state()
    
    if current_state in [VivodState.waiting_for_amount, VivodState.waiting_for_username]:
        await state.clear()  # Сбрасываем состояние
        await message.answer("❌ Вы отменили процесс вывода средств.")
    else:
        await message.answer("❌ Нет активного процесса вывода для отмены.")

@vivod_router.message(VivodState.waiting_for_amount)
async def process_vivod_amount(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной.")
        if amount > user_balances.get(user_id, 0):
            await message.answer("❌ У вас недостаточно средств! Введите сумму заново:")
            return
    except ValueError:
        await message.answer("❌ Некорректная сумма! Введите число:")
        return

    await state.update_data(amount=amount)
    await state.set_state(VivodState.waiting_for_username)
    await message.answer("Теперь введите юзернейм получателя (пример: @durov):")

@vivod_router.message(VivodState.waiting_for_username)
async def process_vivod_username(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    amount = data["amount"]
    username = message.text.strip()

    if not username.startswith("@") or len(username) < 2:
        await message.answer("❌ Некорректный юзернейм! Введите снова:")
        return

    user_balances[user_id] -= amount
    save_balances()
    await state.clear()

    await message.answer(f"✅ Успешно! {amount}$ были отправлены на @unbrokensociety 🎉")


# Main function
async def main():
    global bot
    # Create bot instance
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    # Create dispatcher
    dp = Dispatcher()
    
    # Load user data
    load_balances()
    load_stats()
    
    # Register all routers
    dp.include_router(vivod_router)
    dp.include_router(profile_router)
    dp.include_router(start_router)
    dp.include_router(balance_router)
    dp.include_router(top_router)
    dp.include_router(game_router)
    
    # Start polling
    print("Bot started!")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Error during bot execution: {e}")
    finally:
        # Save user data when bot stops
        print("Saving balances and shutting down...")
        save_balances()
        save_stats()
        await bot.session.close()
        print("Bot stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped manually.")
