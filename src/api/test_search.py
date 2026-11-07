from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from agenda.models import AgendaModel
from main.models import AudioRecording, DrawDocument, Folder, Image, Todo

User = get_user_model()


class GlobalSearchAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="search_user", password="senha123")
        self.other = User.objects.create_user(username="search_other", password="senha123")
        self.folder = Folder.objects.create(user=self.user, name="Pasta Procurada")
        self.todo = Todo.objects.create(
            user=self.user,
            titulo="Tarefa Procurada",
            anotacao="Anotação de teste",
            folder=self.folder,
        )
        self.event = AgendaModel.objects.create(user=self.user, titulo="Evento Procurado")
        self.audio = AudioRecording.objects.create(
            user=self.user, titulo="Áudio Procurado", folder=self.folder
        )
        self.drawing = DrawDocument.objects.create(
            user=self.user, titulo="Desenho Procurado", folder=self.folder
        )
        self.image = Image.objects.create(
            img="imgs/nome-procurado.png",
            titulo="Imagem Procurada",
            todo=self.todo,
        )
        Todo.objects.create(user=self.other, titulo="Tarefa Procurada de outra pessoa")
        self.client.force_authenticate(user=self.user)
        self.url = reverse("api:search")

    def test_search_finds_each_supported_entity_type(self):
        response = self.client.get(self.url, {"q": "procurad"})

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            [result["type"] for result in response.data["results"]],
            ["task", "event", "audio", "drawing", "image", "folder"],
        )
        self.assertEqual(response.data["count"], 6)

    def test_search_filters_by_type_and_creation_date(self):
        response = self.client.get(
            self.url,
            {
                "type": "task",
                "created_after": self.todo.created_at.date().isoformat(),
                "created_before": self.todo.created_at.date().isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.todo.id)

    def test_search_can_find_an_image_by_its_file_name(self):
        response = self.client.get(self.url, {"q": "nome-procurado", "type": "image"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.image.id)

    def test_search_does_not_return_other_users_private_items(self):
        response = self.client.get(self.url, {"q": "procurad"})

        self.assertNotIn(
            "Tarefa Procurada de outra pessoa",
            [result["title"] for result in response.data["results"]],
        )

    def test_search_rejects_invalid_date_ranges(self):
        response = self.client.get(
            self.url,
            {"created_after": "2026-11-08", "created_before": "2026-11-07"},
        )

        self.assertEqual(response.status_code, 400)

    def test_search_rejects_invalid_calendar_dates(self):
        response = self.client.get(self.url, {"created_after": "2026-02-31"})

        self.assertEqual(response.status_code, 400)
