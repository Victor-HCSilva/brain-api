from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from main.models import CollaborationGroup, Folder, Todo

User = get_user_model()


class CollaborationAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="collab_owner", password="senha123")
        self.member = User.objects.create_user(username="collab_member", password="senha123")
        self.other = User.objects.create_user(username="collab_other", password="senha123")
        self.group = CollaborationGroup.objects.create(
            name="Equipe API",
            owner=self.owner,
            descricao="Grupo de teste",
        )

    def test_owner_can_create_group_and_add_member(self):
        self.client.force_authenticate(user=self.owner)
        create_response = self.client.post(
            reverse("api:group-list"),
            {"name": "Novo grupo", "descricao": "Descrição"},
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        group_id = create_response.data["id"]

        member_response = self.client.post(
            reverse("api:group-add-member", kwargs={"pk": group_id}),
            {"user_id": self.member.id},
            format="json",
        )
        self.assertEqual(member_response.status_code, 200)
        self.assertEqual(member_response.data["membros"][0]["id"], self.member.id)

    def test_non_owner_cannot_manage_group_members(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.post(
            reverse("api:group-add-member", kwargs={"pk": self.group.id}),
            {"user_id": self.member.id},
            format="json",
        )
        self.assertIn(response.status_code, [403, 404])

    def test_owner_can_share_todo_with_user_and_group_member_can_access_it(self):
        self.group.membros.add(self.member)
        folder = Folder.objects.create(user=self.owner, name="Pasta compartilhada")
        todo = Todo.objects.create(
            user=self.owner,
            titulo="Todo compartilhado",
            folder=folder,
        )
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            reverse("api:todo-share", kwargs={"pk": todo.id}),
            {"group_ids": [self.group.id]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.client.force_authenticate(user=self.member)
        response = self.client.get(reverse("api:todo-detail", kwargs={"pk": todo.id}))
        self.assertEqual(response.status_code, 200)

    def test_owner_can_share_folder_with_user(self):
        folder = Folder.objects.create(user=self.owner, name="Pasta para compartilhar")
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            reverse("api:folder-share", kwargs={"pk": folder.id}),
            {"user_ids": [self.member.id]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.client.force_authenticate(user=self.member)
        response = self.client.get(reverse("api:folder-detail", kwargs={"pk": folder.id}))
        self.assertEqual(response.status_code, 200)
