from django.db import models


class User(models.Model):
    tg_id = models.BigIntegerField(unique=True)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=50, null=True, blank=True)
    consent_personal_data = models.BooleanField(default=False)

    role = models.CharField(
        max_length=10,
        choices=[
            ('parent', 'Родитель'),
            ('student', 'Ученик'),
        ],
        null=True,
        blank=True
    )

    is_admin = models.BooleanField(
        default=False,
        verbose_name="Администратор (получает AI-отчёты)"
    )

    def __str__(self):
        return f"{self.tg_id} ({self.role})"




class Poll(models.Model):
    is_active = models.BooleanField(default=True)
    QUESTION_TYPES = [
        ("choice", "Опрос с вариантами (1 ответ)"),
        ("multi_choice", "Опрос с несколькими вариантами"),
        ("scale_group", "Группа утверждений (шкала)"),
        ("text", "Открытый вопрос"),
    ]
    role = models.CharField(
        max_length=10,
        choices=[
            ("parent", "Родитель"),
            ("student", "Ученик"),
        ]
    )

    question = models.TextField(
        help_text="Основной текст вопроса или вводный текст"
    )

    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        default="choice"
    )

    options = models.JSONField(
        null=True,
        blank=True,
        help_text=(
            "Для choice: список вариантов ответа.\n"
            "Для scale_group: список утверждений.\n"
            "Для text: оставить пустым."
        )
    )

    order = models.PositiveIntegerField(default=0)

    telegram_poll_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"[{self.question_type}] {self.question[:50]}"




class Answer(models.Model):
    user = models.ForeignKey(
        'polls.User',
        on_delete=models.CASCADE,
        related_name='answers'
    )
    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE
    )
    answer = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.tg_id} → {self.poll.question}"
