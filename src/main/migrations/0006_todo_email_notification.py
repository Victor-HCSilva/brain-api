from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0005_alter_image_data_de_criacao_alter_todo_prazo_final_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="todo",
            name="email_notification_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="todo",
            name="email_notification_message",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="todo",
            name="email_notification_sent_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
    ]
