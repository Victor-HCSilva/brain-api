from datetime import timedelta
from unittest.mock import call, patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from api.models import ScheduledEmailNotification
from api.tasks.send_reminders_task import send_due_email_notifications

User = get_user_model()


class ScheduledEmailNotificationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="scheduled_email_user",
            email="scheduled@example.com",
            password="test-password",
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("api:notification-list")

    def test_user_can_schedule_and_list_notification_for_own_email(self):
        scheduled_at = timezone.now() + timedelta(hours=1)
        response = self.client.post(
            self.url,
            {
                "scheduled_at": scheduled_at.isoformat(),
                "message": "Lembrar de revisar as anotações.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["recipient_email"], self.user.email)
        self.assertEqual(response.data["message"], "Lembrar de revisar as anotações.")
        self.assertIsNone(response.data["sent_at"])

        list_response = self.client.get(self.url)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 1)

    def test_user_cannot_schedule_in_past_or_without_message(self):
        past_response = self.client.post(
            self.url,
            {
                "scheduled_at": (timezone.now() - timedelta(minutes=1)).isoformat(),
                "message": "Mensagem",
            },
            format="json",
        )
        self.assertEqual(past_response.status_code, 400)
        self.assertIn("scheduled_at", past_response.data)

        empty_response = self.client.post(
            self.url,
            {
                "scheduled_at": (timezone.now() + timedelta(hours=1)).isoformat(),
                "message": "   ",
            },
            format="json",
        )
        self.assertEqual(empty_response.status_code, 400)
        self.assertIn("message", empty_response.data)

    def test_user_without_email_cannot_schedule_notification(self):
        self.user.email = ""
        self.user.save(update_fields=["email"])

        response = self.client.post(
            self.url,
            {
                "scheduled_at": (timezone.now() + timedelta(hours=1)).isoformat(),
                "message": "Mensagem",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("recipient_email", response.data)

    def test_user_cannot_list_or_delete_another_users_notification(self):
        other_user = User.objects.create_user(
            username="other_scheduled_user",
            email="other@example.com",
            password="test-password",
        )
        notification = ScheduledEmailNotification.objects.create(
            user=other_user,
            scheduled_at=timezone.now() + timedelta(hours=1),
            message="Privada",
        )

        list_response = self.client.get(self.url)
        delete_response = self.client.delete(
            reverse("api:notification-detail", kwargs={"pk": notification.pk})
        )

        self.assertEqual(list_response.data["count"], 0)
        self.assertEqual(delete_response.status_code, 404)

    @patch("api.tasks.send_reminders_task.SendEmail")
    def test_due_notifications_send_once_using_existing_email_template(self, send_email):
        notification = ScheduledEmailNotification.objects.create(
            user=self.user,
            scheduled_at=timezone.now() - timedelta(minutes=1),
            message="<script>Mensagem de teste</script>",
        )

        sent_count = send_due_email_notifications()
        second_sent_count = send_due_email_notifications()

        self.assertEqual(sent_count, 1)
        self.assertEqual(second_sent_count, 0)
        send_email.assert_called_once_with(
            self.user,
            "&lt;script&gt;Mensagem de teste&lt;/script&gt;",
            "Notificação agendada",
        )
        notification.refresh_from_db()
        self.assertIsNotNone(notification.sent_at)
