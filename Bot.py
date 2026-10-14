# Bot.py — ТИХИЙ ГОРИЗОНТ
# Установка: pip install -r requirements.txt
# Запуск: python Bot.py

import asyncio
import logging
import csv
import os
import re
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ============================================================
# НАСТРОЙКИ — БЕРУТСЯ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ RAILWAY
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or "0")

DIAGNOSTIC_LINK = os.getenv("DIAGNOSTIC_LINK", "https://t.me/roman_psy")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/tihiy_gorizont")
PDF_LINK = os.getenv("PDF_LINK", "https://your-site.ru/pdf")
AUDIO_LINK = os.getenv("AUDIO_LINK", "https://your-site.ru/audio")

LEADS_FILE = "leads.csv"

# ============================================================
# ВОПРОСЫ
# ============================================================
QUESTIONS = [
    {"id": "name", "text": "Как тебя зовут?", "type": "text"},
    {
        "id": "birth_date",
        "text": (
            "Дата рождения?\n\n"
            "Напиши в формате: ДД.ММ.ГГГГ\n"
            "Например: 15.03.1988"
        ),
        "type": "birth_date",
    },
    {"id": "city", "text": "Из какого ты города?", "type": "text"},
    {"id": "contact", "text": "Оставь контакт для связи (телефон или @username):", "type": "text"},
    {
        "id": "tired",
        "text": "1. Просыпаешься уже уставшим?",
        "type": "choice",
        "options": [
            ("Почти всегда", 3),
            ("Часто", 2),
            ("Иногда", 1),
            ("Редко", 0),
        ],
    },
    {
        "id": "vacation",
        "text": "2. Отдых (отпуск, выходные) помогает восстановиться?",
        "type": "choice",
        "options": [
            ("Нет, возвращаюсь в ту же точку", 3),
            ("Помогает на пару дней", 2),
            ("Помогает, но не полностью", 1),
            ("Да, восстанавливаюсь", 0),
        ],
    },
    {
        "id": "joy",
        "text": "3. Когда последний раз чувствовал настоящую радость?",
        "type": "choice",
        "options": [
            ("Не помню", 3),
            ("Больше месяца назад", 2),
            ("На этой неделе", 1),
            ("Сегодня", 0),
        ],
    },
    {
        "id": "body",
        "text": "4. Где чаще всего напряжение в теле?",
        "type": "choice",
        "options": [
            ("Шея, плечи — каменные", 3),
            ("Спина, поясница", 2),
            ("Иногда бывает", 1),
            ("Нет напряжения", 0),
        ],
    },
    {
        "id": "breath",
        "text": "5. Как дышишь?",
        "type": "choice",
        "options": [
            ("Поверхностно, грудью", 3),
            ("Иногда задерживаю дыхание", 2),
            ("Дышу нормально, но не глубоко", 1),
            ("Дышу животом", 0),
        ],
    },
    {
        "id": "energy",
        "text": "6. Как с энергией к вечеру?",
        "type": "choice",
        "options": [
            ("Ноль, только лежать", 3),
            ("Хватает только на базовое", 2),
            ("Иногда есть силы", 1),
            ("Энергии достаточно", 0),
        ],
    },
    {
        "id": "sleep",
        "text": "7. Как спишь?",
        "type": "choice",
        "options": [
            ("Плохо, просыпаюсь ночью", 3),
            ("Засыпаю с трудом", 2),
            ("Нормально, но не высыпаюсь", 1),
            ("Сплю хорошо", 0),
        ],
    },
    {
        "id": "meaning",
        "text": "8. Чувствуешь, что живёшь свою жизнь?",
        "type": "choice",
        "options": [
            ("Нет, живу чужую", 3),
            ("Часто сомневаюсь", 2),
            ("Иногда", 1),
            ("Да, живу свою", 0),
        ],
    },
    {
        "id": "therapy",
        "text": "9. Был ли опыт терапии / работы с психологом?",
        "type": "choice",
        "options": [
            ("Нет, никогда", 0),
            ("Был, но давно", 1),
            ("Работаю сейчас", 2),
            ("Регулярно", 3),
        ],
    },
    {
        "id": "ready",
        "text": "10. Готов к глубокой работе над собой (4 дня без города)?",
        "type": "choice",
        "options": [
            ("Да, готов", 3),
            ("Скорее да", 2),
            ("Сомневаюсь", 1),
            ("Пока не готов", 0),
        ],
    },
    {
        "id": "budget",
        "text": "11. Ретрит стоит от 70 000 руб. Как тебе такой формат?",
        "type": "choice",
        "options": [
            ("Готов оплатить", 3),
            ("Дорого, но подумаю", 2),
            ("Пока не готов", 1),
            ("Точно не готов", 0),
        ],
    },
    {
        "id": "goal",
        "text": "12. Что хочешь изменить в жизни через месяц? (напиши своими словами)",
        "type": "text",
    },
]


# ============================================================
# ВАЛИДАЦИЯ ДАТЫ РОЖДЕНИЯ
# ============================================================
def parse_birth_date(text: str):
    text = text.strip()
    match = re.match(r"^(\d{1,2})[./\-\s](\d{1,2})[./\-\s](\d{4})$", text)
    if not match:
        return None, (
            "Не могу распознать дату.\n\n"
            "Напиши в формате: ДД.ММ.ГГГГ\n"
            "Например: 15.03.1988"
        )

    day = int(match.group(1))
    month = int(match.group(2))
    year = int(match.group(3))

    if not (1 <= day <= 31):
        return None, "День должен быть от 1 до 31. Попробуй ещё раз:"
    if not (1 <= month <= 12):
        return None, "Месяц должен быть от 1 до 12. Попробуй ещё раз:"

    current_year = datetime.now().year
    if not (1900 <= year <= current_year):
        return None, f"Год должен быть от 1900 до {current_year}. Попробуй ещё раз:"

    try:
        birth = datetime(year, month, day)
    except ValueError:
        return None, "Такой даты не существует. Проверь день и месяц. Попробуй ещё раз:"

    today = datetime.now()
    age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))

    if age < 14:
        return None, "Бот для взрослых (14+). Если ошибся — напиши дату ещё раз:"
    if age > 100:
        return None, "Проверь год рождения. Попробуй ещё раз:"

    return birth, age


# ============================================================
# КЛАВИАТУРЫ
# ============================================================
def start_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Начать опрос", callback_data="start_survey")
    kb.button(text="О ретрите", callback_data="about")
    kb.adjust(1)
    return kb.as_markup()


def options_kb(options, qid):
    kb = InlineKeyboardBuilder()
    for i, (text, _) in enumerate(options):
        kb.button(text=text, callback_data=f"ans:{qid}:{i}")
    kb.adjust(1)
    return kb.as_markup()


def result_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Записаться на диагностику", url=DIAGNOSTIC_LINK)
    kb.button(text="Получить PDF-тест", callback_data="get_pdf")
    kb.button(text="Подписаться на канал", url=CHANNEL_LINK)
    kb.adjust(1)
    return kb.as_markup()


# ============================================================
# ЛОГИКА РЕЗУЛЬТАТА
# ============================================================
def get_result(score):
    if score <= 8:
        return {
            "title": "Ты в норме",
            "text": (
                f"Твой результат: {score} баллов.\n\n"
                "Ты пока в ресурсе. Усталость есть, но она восстановимая.\n\n"
                "Что делать:\n"
                "- Сохраняй режим сна\n"
                "- Дыхательные практики 5 мин/день\n"
                "- Раз в месяц — день тишины\n\n"
                "Ретрит тебе пока не нужен. Но если хочешь углубить — приходи на диагностику."
            ),
        }
    elif score <= 17:
        return {
            "title": "Лёгкое выгорание",
            "text": (
                f"Твой результат: {score} баллов.\n\n"
                "Первая стадия. Тело подаёт сигналы, психика — тоже.\n\n"
                "Что делать:\n"
                "- Сменить среду минимум на 2 дня\n"
                "- Работа с дыханием (Александра)\n"
                "- Разобраться, куда уходит энергия (Роман)\n\n"
                "Ретрит «Тихий горизонт» подойдёт идеально — 4 дня в горах.\n"
                "Запишись на бесплатную диагностику."
            ),
        }
    elif score <= 26:
        return {
            "title": "Среднее выгорание",
            "text": (
                f"Твой результат: {score} баллов.\n\n"
                "Вторая стадия. Отдых не помогает, тело в зажимах, энергия на нуле.\n\n"
                "Что делать:\n"
                "- Не ждать, что само пройдёт\n"
                "- Работать с психикой И телом одновременно\n"
                "- 4 дня глубокой работы\n\n"
                "Ретрит «Тихий горизонт» — это твой формат.\n"
                "Роман + Александра работают с головой и энергией.\n\n"
                "Запишись на диагностику — обсудим твой случай."
            ),
        }
    else:
        return {
            "title": "Тяжёлое выгорание",
            "text": (
                f"Твой результат: {score} баллов.\n\n"
                "Третья стадия. Это серьёзно. Нервная система истощена.\n\n"
                "Что делать:\n"
                "- Срочно сменить среду\n"
                "- Профессиональное сопровождение\n"
                "- Работа с психикой + телом + энергией\n\n"
                "Ретрит «Тихий горизонт» + индивидуальные сессии.\n"
                "На диагностике обсудим, подходит ли тебе формат или нужна терапия.\n\n"
                "Не оставайся один. Запишись."
            ),
        }


# ============================================================
# СОХРАНЕНИЕ ЛИДОВ
# ============================================================
def save_lead(answers, score):
    file_exists = os.path.isfile(LEADS_FILE)
    with open(LEADS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "datetime", "name", "birth_date", "age", "city", "contact",
                "score", "tired", "vacation", "joy", "body", "breath",
                "energy", "sleep", "meaning", "therapy", "ready",
                "budget", "goal",
            ])
        writer.writerow([
            datetime.now().isoformat(),
            answers.get("name", ""),
            answers.get("birth_date", ""),
            answers.get("age", ""),
            answers.get("city", ""),
            answers.get("contact", ""),
            score,
            answers.get("tired", ""),
            answers.get("vacation", ""),
            answers.get("joy", ""),
            answers.get("body", ""),
            answers.get("breath", ""),
            answers.get("energy", ""),
            answers.get("sleep", ""),
            answers.get("meaning", ""),
            answers.get("therapy", ""),
            answers.get("ready", ""),
            answers.get("budget", ""),
            answers.get("goal", ""),
        ])


# ============================================================
# ХЕНДЛЕРЫ
# ============================================================
router = Router()


class Survey(StatesGroup):
    in_progress = State()


@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Это бот ретрита «Тихий горизонт».\n\n"
        "Я задам 13 вопросов (2 минуты) и покажу:\n"
        "- Уровень твоего выгорания\n"
        "- Куда утекает энергия\n"
        "- Что делать дальше\n\n"
        "Ретрит ведут: Роман (психолог) и Александра (энергопрактик).\n\n"
        "Готов?",
        reply_markup=start_kb(),
    )


@router.message(F.text == "/help")
async def cmd_help(message: Message):
    await message.answer(
        "Команды:\n"
        "/start — начать опрос\n"
        "/help — помощь\n\n"
        "Вопросы: @roman_psy"
    )


@router.callback_query(F.data == "about")
async def about(callback: CallbackQuery):
    await callback.message.answer(
        "РЕТРИТ «ТИХИЙ ГОРИЗОНТ»\n\n"
        "4 дня в горах Кавказа. Группа 8–10 человек.\n\n"
        "Роман — цифровой психолог\n"
        "Работает с психикой: выгорание, тревога, смыслы.\n\n"
        "Александра — энергопрактик\n"
        "Работает с телом и энергией: дыхание, зажимы, ресурс.\n\n"
        "Что внутри:\n"
        "- Утренние практики (Александра)\n"
        "- Походы с проводником\n"
        "- Вечерние сессии (Роман)\n"
        "- 4 недели интеграции после\n"
        "- Чат выпускников навсегда\n\n"
        "От 70 000 руб.\n\n"
        "Пройти опрос?",
        reply_markup=start_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "start_survey")
async def start_survey(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Survey.in_progress)
    await state.update_data(current=0, answers={}, score=0)
    await callback.message.answer("Отлично! Начинаем. Отвечай честно — это важно.")
    await ask_question(callback.message, state)
    await callback.answer()


async def ask_question(message: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("current", 0)
    if idx >= len(QUESTIONS):
        await finish_survey(message, state)
        return
    q = QUESTIONS[idx]
    if q["type"] == "choice":
        await message.answer(
            q["text"],
            reply_markup=options_kb(q["options"], q["id"]),
        )
    else:
        await message.answer(q["text"])


@router.callback_query(F.data.startswith("ans:"))
async def handle_choice(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Ошибка данных", show_alert=False)
        return
    _, qid, opt_idx = parts
    try:
        opt_idx = int(opt_idx)
    except ValueError:
        await callback.answer("Ошибка данных", show_alert=False)
        return

    q = next((q for q in QUESTIONS if q["id"] == qid), None)
    if q is None or q["type"] != "choice":
        await callback.answer("Вопрос не найден", show_alert=False)
        return

    text, score = q["options"][opt_idx]

    data = await state.get_data()
    answers = data.get("answers", {})
    answers[qid] = text
    total = data.get("score", 0) + score
    await state.update_data(
        answers=answers,
        score=total,
        current=data.get("current", 0) + 1,
    )
    await callback.message.edit_text(f"Принято: {text}")
    await ask_question(callback.message, state)
    await callback.answer()


@router.message(Survey.in_progress)
async def handle_text(message: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("current", 0)
    if idx >= len(QUESTIONS):
        return
    q = QUESTIONS[idx]
    if q["type"] not in ("text", "birth_date"):
        return

    if q["type"] == "birth_date":
        birth, age_or_error = parse_birth_date(message.text or "")
        if birth is None:
            await message.answer(age_or_error)
            return

        answers = data.get("answers", {})
        answers["birth_date"] = birth.strftime("%d.%m.%Y")
        answers["age"] = age_or_error
        await state.update_data(answers=answers, current=idx + 1)
        await message.answer(
            f"Дата рождения: {birth.strftime('%d.%m.%Y')}\n"
            f"Возраст: {age_or_error} лет"
        )
        await ask_question(message, state)
        return

    answers = data.get("answers", {})
    answers[q["id"]] = message.text or ""
    await state.update_data(answers=answers, current=idx + 1)
    await ask_question(message, state)


async def finish_survey(message: Message, state: FSMContext):
    data = await state.get_data()
    score = data.get("score", 0)
    answers = data.get("answers", {})
    result = get_result(score)

    text = (
        f"{result['title']}\n\n"
        f"{result['text']}\n\n"
        "-------------------------\n"
        "Что дальше?\n"
        "Запишись на бесплатную диагностику (30 мин, Zoom).\n"
        "Роман и Александра разберут твой случай лично."
    )
    await message.answer(text, reply_markup=result_kb())

    save_lead(answers, score)

    if ADMIN_ID:
        try:
            await message.bot.send_message(
                ADMIN_ID,
                f"Новый лид!\n\n"
                f"Имя: {answers.get('name')}\n"
                f"Дата рождения: {answers.get('birth_date')} "
                f"({answers.get('age')} лет)\n"
                f"Город: {answers.get('city')}\n"
                f"Контакт: {answers.get('contact')}\n"
                f"Балл: {score}/36\n"
                f"Цель: {answers.get('goal')}",
            )
        except Exception as e:
            logging.warning(f"Не удалось отправить админу: {e}")

    await state.clear()


@router.callback_query(F.data == "get_pdf")
async def get_pdf(callback: CallbackQuery):
    await callback.message.answer(
        f"PDF-тест «7 признаков выгорания»:\n{PDF_LINK}\n\n"
        f"Аудио-медитация от Романа:\n{AUDIO_LINK}\n\n"
        f"Видео-практика от Александры:\n{PDF_LINK}"
    )
    await callback.answer()


# ============================================================
# ЗАПУСК
# ============================================================
async def main():
    logging.basicConfig(level=logging.INFO)
    if not BOT_TOKEN:
        raise RuntimeError("Переменная BOT_TOKEN не задана!")
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    print("Бот «Тихий горизонт» запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")
