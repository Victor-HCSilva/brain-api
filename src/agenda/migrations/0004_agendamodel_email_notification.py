from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("agenda", "0003_alter_agendamodel_importancia"),
    ]

    operations = [
        migrations.AddField(
            model_name="agendamodel",
            name="email_notification_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="agendamodel",
            name="email_notification_message",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="agendamodel",
            name="email_notification_sent_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
    ]
