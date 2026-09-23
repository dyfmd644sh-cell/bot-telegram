import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
 
# ============ НАСТРОЙКИ ============
BOT_TOKEN = "8607657363:AAGYLbOlt0yCTtqzf9I8uqsY_7XnTMSwMT8"
LINK_TO_COURSE = "https://t.me/roman_schedrov"
 
logging.basicConfig(level=logging.INFO)
 
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
 
# ============ ВОПРОСЫ ТЕСТА ============
QUESTIONS = [
    "Я беру телефон в руки в первые 5 минут после пробуждения",
    "Я проверяю телефон, даже когда он не вибрировал",
    "Я листаю ленту, не помня, что искал",
    "Я чувствую тревогу, если телефон не рядом",
    "Я сравниваю свою жизнь с тем, что вижу у других",
    "Я откладываю дела ради «ещё 5 минут в телефоне»",
    "Я чувствую пустоту после долгого скроллинга",
    "Я проверяю новости/сообщения по 10+ раз в день",
]
 
ANSWERS = [
    ("Никогда", 1),
    ("Иногда", 2),
    ("Часто", 3),
    ("Всегда", 4),
]
 
# ============ СОСТОЯНИЯ ============
class Quiz(StatesGroup):
    answering = State()
 
# ============ КЛАВИАТУРЫ ============
def start_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 Пройти тест", callback_data="start_test")],
        [InlineKeyboardButton(text="📚 О курсе", callback_data="about_course")],
    ])
 
def answers_kb():
    buttons = [
        [InlineKeyboardButton(text=f"{text} ({score})", callback_data=f"ans_{score}")]
        for text, score in ANSWERS
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
 
def result_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Забрать курс за 490 ₽", url=LINK_TO_COURSE)],
        [InlineKeyboardButton(text="🔁 Пройти заново", callback_data="start_test")],
    ])
 
# ============ ЛОГИКА ОПРЕДЕЛЕНИЯ ТИПА ============
def get_profile(score: int) -> dict:
    """score: от 8 до 32"""
    if score <= 16:
        return {
            "type": "FOMO-залипала",
            "emoji": "😰",
            "desc": (
                "Ты сравниваешь свою реальность с чужими хайлайтами "
                "и боишься что-то пропустить. Это не зависть — это биология."
            ),
            "advice": "Урок 4 про эмоциональную разгрузку — твой ключевой."
        }
    elif score <= 24:
        return {
            "type": "Тревожный чекер",
            "emoji": "📱",
            "desc": (
                "Ты проверяешь телефон и новости каждые 5 минут. "
                "Мозг не отличает заголовок от реальной угрозы — отсюда тревога."
            ),
            "advice": "Урок 3 про цифровую гигиену спасёт тебя."
        }
    else:
        return {
            "type": "Скроллер-зомби",
            "emoji": "🧟",
            "desc": (
                "Ты листаешь без цели и не помнишь, что искал. "
                "Дофаминовая петля держит крепче всего."
            ),
            "advice": "Начни с Урока 2 про дофаминовую петлю."
        }
 
# ============ ХЭНДЛЕРЫ ============
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я помогу тебе узнать твой цифровой профиль — "
        "тип зависимости от телефона.\n\n"
        "Это займёт 2 минуты. Готов?",
        reply_markup=start_kb()
    )
 
@dp.callback_query(F.data == "about_course")
async def about_course(callback: CallbackQuery):
    await callback.message.answer(
        "📚 *Мини-курс «Цифровая психология»*\n\n"
        "5 уроков по 7-12 минут:\n"
        "1. Диагностика\n"
        "2. Дофаминовая петля\n"
        "3. Цифровая гигиена\n"
        "4. Разгрузка от тревоги\n"
        "5. Твой цифровой кодекс\n\n"
        "💰 Цена: 1 490 ₽\n"
        "🔥 Первым 10 — 490 ₽\n\n"
        "Жми кнопку ниже 👇",
        parse_mode="Markdown",
        reply_markup=result_kb()
    )
    await callback.answer()
 
@dp.callback_query(F.data == "start_test")
async def start_test(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Quiz.answering)
    await state.update_data(current=0, total=0)
    await callback.message.answer(
        "Поехали! Отвечай честно — это для тебя.\n\n"
        f"❓ *Вопрос 1 из {len(QUESTIONS)}*\n\n"
        f"{QUESTIONS[0]}",
        parse_mode="Markdown",
        reply_markup=answers_kb()
    )
    await callback.answer()
 
@dp.callback_query(Quiz.answering, F.data.startswith("ans_"))
async def handle_answer(callback: CallbackQuery, state: FSMContext):
    score = int(callback.data.split("_")[1])
    data = await state.get_data()
    current = data["current"]
    total = data["total"] + score
 
    current += 1
 
    if current < len(QUESTIONS):
        await state.update_data(current=current, total=total)
        await callback.message.edit_text(
            f"❓ *Вопрос {current + 1} из {len(QUESTIONS)}*\n\n"
            f"{QUESTIONS[current]}",
            parse_mode="Markdown",
            reply_markup=answers_kb()
        )
    else:
        # ФИНАЛ
        await state.clear()
        profile = get_profile(total)
 
        text = (
            f"🎯 *Твой результат*\n\n"
            f"{profile['emoji']} *{profile['type']}*\n\n"
            f"{profile['desc']}\n\n"
            f"💡 {profile['advice']}\n\n"
            f"Твой балл: *{total} из 32*\n\n"
            "За 5 дней ты можешь выйти из этого состояния. "
            "Мини-курс — твой следующий шаг."
        )
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=result_kb()
        )
 
    await callback.answer()
 
@dp.message()
async def fallback(message: Message):
    await message.answer(
        "Я понимаю только команды. Напиши /start чтобы начать.",
        reply_markup=start_kb()
    )
 
# ============ ЗАПУСК ============
async def main():
    print("🤖 Бот запущен...")
    await dp.start_polling(bot)
 
if __name__ == "__main__":
    asyncio.run(main())