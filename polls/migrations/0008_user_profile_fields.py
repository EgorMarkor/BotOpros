from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('polls', '0007_user_is_admin_alter_poll_question_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='full_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='phone_number',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='consent_personal_data',
            field=models.BooleanField(default=False),
        ),
    ]
