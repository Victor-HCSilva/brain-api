from html import escape

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from agenda.models import AgendaModel
from api.email.script import SendEmail
from api.models import ScheduledEmailNotification
from main.models import Todo


def _send_due_notifications(queryset) -> int:
    sent_count = 0
    now = timezone.now()

    for item in queryset.select_related("user"):
        manager = type(item)._default_manager
        with transaction.atomic():
            try:
                locked_item = manager.select_for_update().get(
                    pk=item.pk,
                    is_active=True,
                    email_notification_at=item.email_notification_at,
                    email_notification_message=item.email_notification_message,
                    email_notification_sent_at__isnull=True,
                    email_notification_at__lte=now,
                )
            except type(item).DoesNotExist:
                continue

            title = f"Lembrete de {locked_item.titulo}"
            message = locked_item.email_notification_message.strip() or title
            SendEmail(locked_item.user, escape(message), title).send()
            locked_item.email_notification_sent_at = timezone.now()
            locked_item.save(update_fields=["email_notification_sent_at"])
        sent_count += 1

    return sent_count


@shared_task
def send_due_email_notifications() -> int:
    now = timezone.now()
    todos = Todo.objects.filter(
        is_active=True,
        email_notification_at__lte=now,
        email_notification_sent_at__isnull=True,
    )
    events = AgendaModel.objects.filter(
        is_active=True,
        email_notification_at__lte=now,
        email_notification_sent_at__isnull=True,
    )
    sent_count = _send_due_notifications(todos) + _send_due_notifications(events)
    due_notifications = ScheduledEmailNotification.objects.filter(
        is_active=True,
        sent_at__isnull=True,
        scheduled_at__lte=now,
    ).select_related("user")

    for notification in due_notifications:
        with transaction.atomic():
            try:
                locked_notification = ScheduledEmailNotification.objects.select_for_update().get(
                    pk=notification.pk,
                    is_active=True,
                    sent_at__isnull=True,
                    scheduled_at=notification.scheduled_at,
                    scheduled_at__lte=now,
                )
            except ScheduledEmailNotification.DoesNotExist:
                continue

            title = "From Brain - Notificação"
            SendEmail(
                locked_notification.user,
                escape(locked_notification.message),
                title,
            ).send()
            locked_notification.sent_at = timezone.now()
            locked_notification.save(update_fields=["sent_at", "updated_at"])
        sent_count += 1

    return sent_count
