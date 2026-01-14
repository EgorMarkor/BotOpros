from ..models import Answer
from .prompts import PARENT_REPORT_PROMPT
from django.conf import settings
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def build_user_answers(user):
    answers = (
        Answer.objects
        .filter(user=user)
        .select_related("poll")
        .order_by("created_at")
    )

    text = ""
    for ans in answers:
        text += f"- {ans.poll.question} — {ans.answer}\n"

    return text


def build_parent_answers():
    answers = (
        Answer.objects
        .filter(user__role="parent")
        .select_related("poll", "user")
        .order_by("user_id", "created_at")
    )

    if not answers.exists():
        return ""

    text = ""
    current_user_id = None
    for ans in answers:
        if current_user_id != ans.user_id:
            current_user_id = ans.user_id
            text += f"\nРеспондент {ans.user.tg_id}:\n"

        text += f"- {ans.poll.question} — {ans.answer}\n"

    return text.strip()


def generate_ai_report(user):
    data = build_user_answers(user)
    prompt = PARENT_REPORT_PROMPT.format(data=data)

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # можно gpt-4o
        messages=[
            {"role": "system", "content": "Ты профессиональный аналитик."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )

    return response.choices[0].message.content


def generate_parent_report_for_all():
    data = build_parent_answers()

    if not data:
        return ""

    prompt = PARENT_REPORT_PROMPT.format(data=data)

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # можно gpt-4o
        messages=[
            {"role": "system", "content": "Ты профессиональный аналитик."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )

    return response.choices[0].message.content
