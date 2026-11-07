from datetime import timedelta
from unittest.mock import call, patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from agenda.models import AgendaModel
from api.tasks.send_reminders_task import send_due_email_notifications
from main.models import Todo

User = get_user_model()


class EmailNotificationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="notification_user",
            email="notification@example.com",
            password="senha123",
        )
        self.client.force_authenticate(user=self.user)

    def test_owner_can_create_todo_with_email_notification(self):
        notification_at = timezone.now() + timedelta(hours=1)

        with patch("api.serializers.todo.send_delay.delay"):
            response = self.client.post(
                reverse("api:todo-list"),
                {
                    "titulo": "Revisar matéria",
                    "anotacao": "Capítulo 2",
                    "prioridade": "Média",
                    "tag": "Tarefa",
                    "email_notification_at": notification_at.isoformat(),
                    "email_notification_message": "Revisar o capítulo antes da prova.",
                    "email_notification_sent_at": notification_at.isoformat(),
                },
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["email_notification_message"],
            "Revisar o capítulo antes da prova.",
        )
        self.assertIsNotNone(response.data["email_notification_at"])
        self.assertIsNone(response.data["email_notification_sent_at"])

    def test_user_without_email_cannot_schedule_notification(self):
        self.user.email = ""
        self.user.save(update_fields=["email"])

        response = self.client.post(
            reverse("api:todo-list"),
            {
                "titulo": "Tarefa sem e-mail",
                "anotacao": "Detalhes",
                "email_notification_at": (timezone.now() + timedelta(hours=1)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email_notification_at", response.data)

    def test_owner_can_create_agenda_event_with_email_notification(self):
        notification_at = timezone.now() + timedelta(hours=1)

        response = self.client.post(
            reverse("api:agenda-list"),
            {
                "titulo": "Prova",
                "descricao": "Sala 12",
                "tipo_de_evento": "Prova",
                "importancia": "2",
                "dia_do_evento": notification_at.isoformat(),
                "email_notification_at": notification_at.isoformat(),
                "email_notification_message": "Levar documento.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        event = response.data["evento"]
        self.assertEqual(event["email_notification_message"], "Levar documento.")
        self.assertIsNotNone(event["email_notification_at"])

    def test_rescheduling_sent_todo_rearms_notification(self):
        todo = Todo.objects.create(
            user=self.user,
            titulo="Revisar matéria",
            anotacao="Capítulo 2",
            email_notification_at=timezone.now() - timedelta(minutes=1),
            email_notification_sent_at=timezone.now() - timedelta(minutes=1),
        )
        notification_at = timezone.now() + timedelta(hours=2)

        with patch("api.serializers.todo.send_delay.delay"):
            response = self.client.patch(
                reverse("api:todo-detail", kwargs={"pk": todo.pk}),
                {
                    "email_notification_at": notification_at.isoformat(),
                    "email_notification_message": "Nova data.",
                },
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["email_notification_sent_at"])


class ScheduledEmailNotificationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reminder_user",
            email="reminder@example.com",
            password="senha123",
        )

    @patch("api.tasks.send_reminders_task.SendEmail")
    def test_due_todo_and_agenda_notifications_are_sent_once(self, send_email):
        due_at = timezone.now() - timedelta(minutes=1)
        todo = Todo.objects.create(
            user=self.user,
            titulo="Revisar tarefa",
            anotacao="Anotações",
            email_notification_at=due_at,
            email_notification_message="<script>mensagem</script>",
        )
        second_todo = Todo.objects.create(
            user=self.user,
            titulo="Outra tarefa",
            anotacao="Mais anotações",
            email_notification_at=due_at,
        )
        event = AgendaModel.objects.create(
            user=self.user,
            titulo="Prova",
            dia_do_evento=due_at,
            email_notification_at=due_at,
        )

        sent_count = send_due_email_notifications()
        second_sent_count = send_due_email_notifications()

        self.assertEqual(sent_count, 3)
        self.assertEqual(second_sent_count, 0)
        send_email.assert_has_calls(
            [
                call(self.user, "&lt;script&gt;mensagem&lt;/script&gt;", "Lembrete de Revisar tarefa"),
                call(self.user, "Lembrete de Outra tarefa", "Lembrete de Outra tarefa"),
                call(self.user, "Lembrete de Prova", "Lembrete de Prova"),
            ],
            any_order=True,
        )
        todo.refresh_from_db()
        second_todo.refresh_from_db()
        event.refresh_from_db()
        self.assertIsNotNone(todo.email_notification_sent_at)
        self.assertIsNotNone(second_todo.email_notification_sent_at)
        self.assertIsNotNone(event.email_notification_sent_at)

    @patch("api.tasks.send_reminders_task.SendEmail")
    def test_failed_email_delivery_can_be_retried(self, send_email):
        todo = Todo.objects.create(
            user=self.user,
            titulo="Tarefa",
            anotacao="Anotações",
            email_notification_at=timezone.now() - timedelta(minutes=1),
        )
        send_email.return_value.send.side_effect = RuntimeError("SMTP indisponível")

        with self.assertRaisesRegex(RuntimeError, "SMTP indisponível"):
            send_due_email_notifications()

        todo.refresh_from_db()
        self.assertIsNone(todo.email_notification_sent_at)
