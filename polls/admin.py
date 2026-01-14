from django.contrib import admin
from django.conf import settings
import requests

from .models import User, Poll, Answer
from .ai.report import generate_parent_report_for_all
from .ai.docx import build_docx_bytes


# ======================================================
# INLINE: ответы пользователя (красивая смета)
# ======================================================

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    can_delete = False
    readonly_fields = ("pretty_poll", "pretty_answer", "created_at")
    fields = ("pretty_poll", "pretty_answer", "created_at")

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Вопрос")
    def pretty_poll(self, obj):
        poll = obj.poll

        if poll.question_type == "scale_group":
            try:
                letter, _ = obj.answer.split(":")
                letter = letter.strip()

                for opt in poll.options:
                    if opt.get("key") == letter:
                        return f"{poll.question}\n— {letter}) {opt.get('text')}"

                return poll.question
            except Exception:
                return poll.question

        return poll.question

    @admin.display(description="Ответ")
    def pretty_answer(self, obj):
        if obj.poll.question_type == "scale_group":
            try:
                return obj.answer.split(":")[1].strip()
            except Exception:
                return obj.answer

        return obj.answer


# ======================================================
# ACTION: AI-ОТЧЁТ → Telegram
# ======================================================

@admin.action(description="🤖 Сформировать AI-отчёт по всем анкетам и отправить админу")
def send_ai_report(modeladmin, request, queryset):
    admins = User.objects.filter(is_admin=True)

    if not admins.exists():
        modeladmin.message_user(
            request,
            "❌ Нет пользователей с флагом is_admin",
            level="error"
        )
        return

    if not getattr(settings, "BOT_TOKEN", None):
        modeladmin.message_user(
            request,
            "❌ BOT_TOKEN не задан в settings.py",
            level="error"
        )
        return

    if not getattr(settings, "OPENAI_API_KEY", None):
        modeladmin.message_user(
            request,
            "❌ OPENAI_API_KEY не задан в settings.py",
            level="error"
        )
        return

    try:
        report_text = generate_parent_report_for_all()
    except Exception as e:
        modeladmin.message_user(
            request,
            f"❌ Ошибка генерации AI-отчёта: {e}",
            level="error"
        )
        return

    if not report_text:
        modeladmin.message_user(
            request,
            "❌ Нет анкет родителей для анализа",
            level="error"
        )
        return

    report_docx = build_docx_bytes(report_text)
    for admin_user in admins:
        try:
            requests.post(
                f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendDocument",
                data={
                    "chat_id": admin_user.tg_id,
                    "caption": "AI-отчёт по анкетам родителей (Word)",
                },
                files={
                    "document": (
                        "parent_report.docx",
                        report_docx,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
                timeout=30,
            )
        except Exception as e:
            modeladmin.message_user(
                request,
                f"❌ Ошибка отправки админу {admin_user.tg_id}: {e}",
                level="error"
            )

    modeladmin.message_user(
        request,
        "✅ AI-отчёт успешно сформирован и отправлен"
    )


# ======================================================
# USER
# ======================================================

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("tg_id", "role", "is_admin")
    list_filter = ("role", "is_admin")
    search_fields = ("tg_id",)
    ordering = ("tg_id",)
    inlines = [AnswerInline]
    actions = [send_ai_report]


# ======================================================
# POLL
# ======================================================

@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = (
        "question",
        "role",
        "question_type",
        "order",
        "is_active",
    )
    list_filter = (
        "role",
        "question_type",
        "is_active",
    )
    ordering = ("order",)
    search_fields = ("question",)


# ======================================================
# ANSWER
# ======================================================

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("user", "poll", "answer", "created_at")
    list_filter = ("poll", "user")
    search_fields = ("answer",)
    ordering = ("-created_at",)
