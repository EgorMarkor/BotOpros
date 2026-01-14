import asyncio
import os
import django

from aiogram import Bot, Dispatcher
from aiogram.types import (
    Message,
    PollAnswer,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command
from asgiref.sync import sync_to_async
from dotenv import load_dotenv


# ---------- ENV ----------
load_dotenv()

BOT_TOKEN = "8532414217:AAGp9-3NXeeFUw0QDblJipK5n6Q96Em8Xo4"
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not found in .env")


# ---------- DJANGO ----------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tg_poll_project.settings")
django.setup()

from polls.models import User, Poll, Answer  # noqa: E402


# ---------- BOT ----------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ---------- STATE (IN MEMORY) ----------
user_progress = {}            # user_id -> index of poll
waiting_text_answer = {}      # user_id -> poll_id
waiting_scale_answer = {}     # user_id -> scale state


# ---------- ROLE KEYBOARD ----------
def role_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👨‍👩‍👧 Я родитель", callback_data="role_parent")],
            [InlineKeyboardButton(text="🎓 Я ученик", callback_data="role_student")],
        ]
    )


# ---------- /start ----------
@dp.message(Command("start"))
async def start_handler(message: Message):
    user, _ = await sync_to_async(User.objects.get_or_create)(
        tg_id=message.from_user.id
    )

    if not user.role:
        await message.answer("Кто вы?", reply_markup=role_keyboard())
    else:
        user_progress[message.from_user.id] = 0
        await message.answer("Начинаем опрос 👇")
        await send_next_poll(message.from_user.id)


# ---------- /change_role ----------
@dp.message(Command("change_role"))
async def change_role_handler(message: Message):
    user = await sync_to_async(User.objects.get)(tg_id=message.from_user.id)
    user.role = None
    await sync_to_async(user.save)()

    user_progress.pop(message.from_user.id, None)
    waiting_text_answer.pop(message.from_user.id, None)
    waiting_scale_answer.pop(message.from_user.id, None)

    await message.answer("Хорошо, давай выберем заново 👇", reply_markup=role_keyboard())


# ---------- ROLE CALLBACK ----------
@dp.callback_query(lambda c: c.data.startswith("role_"))
async def role_callback(callback: CallbackQuery):
    role = callback.data.replace("role_", "")

    user = await sync_to_async(User.objects.get)(tg_id=callback.from_user.id)
    user.role = role
    await sync_to_async(user.save)()

    user_progress[callback.from_user.id] = 0

    await callback.message.edit_text("Роль сохранена ✅\nНачинаем опрос 👇")
    await send_next_poll(callback.from_user.id)


# ---------- SEND NEXT POLL ----------
async def send_next_poll(user_id: int):
    user = await sync_to_async(User.objects.get)(tg_id=user_id)
    index = user_progress.get(user_id, 0)

    polls = await sync_to_async(list)(
        Poll.objects.filter(
            role=user.role,
            is_active=True
        ).order_by("order", "id")
    )

    if index >= len(polls):
        await bot.send_message(user_id, "Спасибо! Опрос завершён ✅")
        return

    poll = polls[index]

    # ---- choice ----
    if poll.question_type == "choice":
        msg = await bot.send_poll(
            chat_id=user_id,
            question=poll.question,
            options=[opt["text"] for opt in poll.options],
            is_anonymous=False
        )

        await sync_to_async(
            Poll.objects.filter(id=poll.id).update
        )(telegram_poll_id=msg.poll.id)

    # ---- text ----
    elif poll.question_type == "text":
        await bot.send_message(user_id, poll.question)
        waiting_text_answer[user_id] = poll.id

    # ---- scale group ----
    elif poll.question_type == "scale_group":
        await bot.send_message(user_id, poll.question)
        await start_scale_group_flow(user_id, poll)


# ---------- SCALE GROUP FLOW ----------
async def start_scale_group_flow(user_id, poll):
    waiting_scale_answer[user_id] = {
        "poll_id": poll.id,
        "options": poll.options,
        "index": 0
    }

    first = poll.options[0]
    await bot.send_message(
        user_id,
        f"{first['key']}) {first['text']}\n\nОцени от 1 до 10"
    )


# ---------- HANDLE POLL ANSWER ----------
@dp.poll_answer()
async def poll_answer_handler(answer: PollAnswer):
    user_id = answer.user.id

    user = await sync_to_async(User.objects.get)(tg_id=user_id)

    poll = await sync_to_async(
        lambda: Poll.objects.filter(telegram_poll_id=answer.poll_id).first()
    )()

    if not poll:
        return

    # 🔥 ВАЖНО: перебираем ВСЕ выбранные варианты
    for index in answer.option_ids:
        selected_text = poll.options[index]["text"]

        await sync_to_async(Answer.objects.create)(
            user=user,
            poll=poll,
            answer=selected_text
        )

    user_progress[user_id] = user_progress.get(user_id, 0) + 1
    await send_next_poll(user_id)


# ---------- HANDLE TEXT ANSWER ----------
@dp.message()
async def handle_text_and_scale(message: Message):
    user_id = message.from_user.id
    text = message.text

    # ----- SCALE GROUP -----
    if user_id in waiting_scale_answer:
        try:
            value = int(text)
            if not 1 <= value <= 10:
                raise ValueError
        except ValueError:
            await message.answer("Пожалуйста, введи число от 1 до 10")
            return

        state = waiting_scale_answer[user_id]
        poll_id = state["poll_id"]
        options = state["options"]
        idx = state["index"]

        poll = await sync_to_async(Poll.objects.get)(id=poll_id)
        user = await sync_to_async(User.objects.get)(tg_id=user_id)

        current = options[idx]

        await sync_to_async(Answer.objects.create)(
            user=user,
            poll=poll,
            answer=f"{current['key']}: {value}"
        )

        state["index"] += 1

        if state["index"] < len(options):
            next_opt = options[state["index"]]
            await message.answer(
                f"{next_opt['key']}) {next_opt['text']}\n\nОцени от 1 до 10"
            )
        else:
            waiting_scale_answer.pop(user_id)
            user_progress[user_id] = user_progress.get(user_id, 0) + 1
            await send_next_poll(user_id)

        return

    # ----- TEXT ANSWER -----
    if user_id in waiting_text_answer:
        poll_id = waiting_text_answer.pop(user_id)

        poll = await sync_to_async(Poll.objects.get)(id=poll_id)
        user = await sync_to_async(User.objects.get)(tg_id=user_id)

        await sync_to_async(Answer.objects.create)(
            user=user,
            poll=poll,
            answer=text
        )

        user_progress[user_id] = user_progress.get(user_id, 0) + 1
        await send_next_poll(user_id)


# ---------- START ----------
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
