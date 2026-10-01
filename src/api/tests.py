from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from main.models import Folder, Todo

User = get_user_model()


class AuthAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="api_user",
            password="senha123",
        )

    def test_token_endpoint_returns_tokens_for_valid_credentials(self):
        url = reverse("api:token_obtain_pair")
        response = self.client.post(
            url,
            {"username": "api_user", "password": "senha123"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_token_endpoint_rejects_invalid_credentials(self):
        url = reverse("api:token_obtain_pair")
        response = self.client.post(
            url,
            {"username": "api_user", "password": "senha_errada"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_me_endpoint_requires_authentication(self):
        url = reverse("api:me")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 401)

    def test_me_endpoint_returns_authenticated_user_data(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("api:me")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "api_user")


class TodoAndFolderAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="senha123")
        self.other = User.objects.create_user(username="other", password="senha123")
        self.folder = Folder.objects.create(user=self.owner, name="Pasta do owner")
        self.todo = Todo.objects.create(
            user=self.owner,
            titulo="Todo do owner",
            anotacao="Texto inicial",
            folder=self.folder,
            is_active=True,
        )

    def test_owner_can_create_todo_through_api(self):
        self.client.force_authenticate(user=self.owner)
        url = reverse("api:todo-list")
        response = self.client.post(
            url,
            {
                "titulo": "Novo todo",
                "anotacao": "Conteúdo",
                "prioridade": "Média",
                "tag": "Tarefa",
                "folder": self.folder.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["titulo"], "Novo todo")
        self.assertEqual(response.data["user"], self.owner.id)

    def test_other_user_cannot_access_owner_todo(self):
        self.client.force_authenticate(user=self.other)
        url = reverse("api:todo-detail", kwargs={"pk": self.todo.pk})
        response = self.client.get(url)

        self.assertIn(response.status_code, [403, 404])

    def test_todo_list_can_filter_by_folder_and_unfiled_tasks(self):
        self.client.force_authenticate(user=self.owner)
        unfiled_todo = Todo.objects.create(
            user=self.owner,
            titulo="Todo sem pasta",
            anotacao="Texto",
            folder=None,
            is_active=True,
        )
        url = reverse("api:todo-list")

        folder_response = self.client.get(url, {"folder": self.folder.id})
        unfiled_response = self.client.get(url, {"folder": "none"})

        self.assertEqual(folder_response.status_code, 200)
        self.assertEqual([todo["id"] for todo in folder_response.data["results"]], [self.todo.id])
        self.assertEqual(unfiled_response.status_code, 200)
        self.assertEqual(
            [todo["id"] for todo in unfiled_response.data["results"]], [unfiled_todo.id]
        )


class SwaggerAPITests(APITestCase):
    def test_schema_and_swagger_ui_are_available(self):
        schema_response = self.client.get(reverse("schema"))
        swagger_response = self.client.get(reverse("swagger-ui"))

        self.assertEqual(schema_response.status_code, 200)
        self.assertEqual(swagger_response.status_code, 200)


class ImageAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner_images", password="senha123")
        self.other = User.objects.create_user(username="other_images", password="senha123")
        self.folder = Folder.objects.create(user=self.owner, name="Pasta de imagens")
        self.todo = Todo.objects.create(
            user=self.owner,
            titulo="Todo com imagem",
            anotacao="Texto inicial",
            folder=self.folder,
            is_active=True,
        )

    def test_owner_can_upload_image_to_todo(self):
        self.client.force_authenticate(user=self.owner)
        url = reverse("api:image-list")
        from django.core.files.uploadedfile import SimpleUploadedFile

        # 1x1 transparent GIF
        gif_bytes = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04"
            b"\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        img_file = SimpleUploadedFile("test.gif", gif_bytes, content_type="image/gif")

        response = self.client.post(
            url,
            {
                "img": img_file,
                "descricao": "Imagem de teste",
                "titulo": "Imagem da tarefa",
                "todo": self.todo.id,
                "observacao": "Observação teste",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["titulo"], "Imagem da tarefa")

    def test_other_user_cannot_upload_image_to_todo(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.other)
        url = reverse("api:image-list")
        gif_bytes = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04"
            b"\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        img_file = SimpleUploadedFile("test2.gif", gif_bytes, content_type="image/gif")
        response = self.client.post(
            url,
            {
                "img": img_file,
                "descricao": "Imagem inválida",
                "titulo": "Sem permissão",
                "todo": self.todo.id,
                "observacao": "Observação",
            },
            format="multipart",
        )

        self.assertIn(response.status_code, [400, 403])

    def test_owner_can_list_his_todos(self):
        self.client.force_authenticate(user=self.owner)
        url = reverse("api:todo-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_owner_can_create_folder_through_api(self):
        self.client.force_authenticate(user=self.owner)
        url = reverse("api:folder-list")
        response = self.client.post(
            url,
            {"name": "Nova pasta"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Nova pasta")

    def test_other_user_cannot_access_owner_folder(self):
        self.client.force_authenticate(user=self.other)
        url = reverse("api:folder-detail", kwargs={"pk": self.folder.pk})
        response = self.client.get(url)

        self.assertIn(response.status_code, [403, 404])
