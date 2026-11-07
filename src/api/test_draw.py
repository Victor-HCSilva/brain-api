from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from main.models import DrawDocument, Folder, Todo

User = get_user_model()


class DrawAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="draw_owner", password="test-pass")
        self.other = User.objects.create_user(username="draw_other", password="test-pass")
        self.folder = Folder.objects.create(user=self.owner, name="Pasta de desenhos")
        self.todo = Todo.objects.create(user=self.owner, titulo="Planejar protótipo", is_active=True)

    def test_owner_can_create_independent_drawing_in_optional_folder(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            reverse("api:drawing-list"),
            {"titulo": "Rascunho", "folder": self.folder.pk, "drawing": []},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["folder"], self.folder.pk)
        self.assertEqual(response.data["drawing"], [])

    def test_owner_can_link_drawing_to_task_later(self):
        self.client.force_authenticate(user=self.owner)
        drawing = DrawDocument.objects.create(user=self.owner, titulo="Ideia")

        response = self.client.post(
            reverse("api:draw-linker-list"),
            {"drawing": drawing.pk, "todo": self.todo.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["desenho_titulo"], drawing.titulo)
        self.assertEqual(response.data["todo_titulo"], self.todo.titulo)

    def test_drawing_validation_rejects_unknown_shapes_and_unsafe_fields(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            reverse("api:drawing-list"),
            {
                "titulo": "Desenho inválido",
                "drawing": [{
                    "id": "shape-1",
                    "type": "script",
                    "text": "<script>alert(1)</script>",
                    "color": "#000000",
                    "strokeWidth": 3,
                }],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("drawing", response.data)

    def test_owner_can_save_freehand_shapes_text_and_requested_geometric_shapes(self):
        self.client.force_authenticate(user=self.owner)
        drawing = DrawDocument.objects.create(user=self.owner, titulo="Formas")
        elements = [
            {"id": "path-1", "type": "path", "points": [[1, 2], [30, 40]], "color": "#25282d", "strokeWidth": 4},
            {"id": "text-1", "type": "text", "x": 20, "y": 30, "text": "Olá", "color": "#25282d", "fontSize": 24},
            {"id": "rect-1", "type": "rect", "x": 10, "y": 10, "width": 80, "height": 60, "color": "#25282d", "strokeWidth": 4},
            {"id": "round-1", "type": "roundRect", "x": 100, "y": 10, "width": 80, "height": 60, "color": "#25282d", "strokeWidth": 4},
            {"id": "circle-1", "type": "circle", "x": 250, "y": 60, "radius": 40, "color": "#25282d", "strokeWidth": 4},
            {"id": "arrow-1", "type": "arrow", "x1": 10, "y1": 100, "x2": 100, "y2": 100, "color": "#25282d", "strokeWidth": 4},
        ]

        response = self.client.patch(
            reverse("api:drawing-detail", kwargs={"pk": drawing.pk}),
            {"drawing": elements},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["drawing"], elements)

    def test_other_user_cannot_list_or_link_an_owner_drawing(self):
        drawing = DrawDocument.objects.create(user=self.owner, titulo="Privado")
        self.client.force_authenticate(user=self.other)

        list_response = self.client.get(reverse("api:drawing-list"))
        link_response = self.client.post(
            reverse("api:draw-linker-list"),
            {"drawing": drawing.pk, "todo": self.todo.pk},
            format="json",
        )

        self.assertEqual(list_response.data["results"], [])
        self.assertEqual(link_response.status_code, 400)
        self.assertFalse(drawing.vinculos_todo.exists())
