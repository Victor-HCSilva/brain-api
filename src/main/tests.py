from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from agenda.models import AgendaModel, Colors
from main.models import Folder, Image, Todo


# ==============================================================================
# Helpers
# ==============================================================================


def make_user(username, password="senha123"):
    return User.objects.create_user(username=username, password=password)


# ==============================================================================
# Testes existentes
# ==============================================================================


class HomeViewTests(TestCase):
    def test_home_renders_existing_template_for_authenticated_user(self):
        user = make_user("tester")
        self.client.force_login(user)

        response = self.client.get(reverse("main:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base/home.html")


# ==============================================================================
# Testes de Autorização — Acesso não autenticado
# ==============================================================================


class UnauthenticatedAccessTests(TestCase):
    """Garante que endpoints protegidos redirecionam usuários não autenticados."""

    def setUp(self):
        self.user = make_user("owner")
        self.todo = Todo.objects.create(user=self.user, titulo="Todo privado", is_active=True)
        self.folder = Folder.objects.create(user=self.user, name="Pasta privada")

    def _assert_redirects_to_login(self, url):
        response = self.client.get(url)
        self.assertIn(response.status_code, [302, 301])
        self.assertIn("/login", response["Location"])

    def test_anotacoes_requires_login(self):
        self._assert_redirects_to_login(reverse("main:anotacoes", kwargs={"id_user": self.user.id}))

    def test_show_requires_login(self):
        self._assert_redirects_to_login(
            reverse(
                "main:show",
                kwargs={"id_user": self.user.id, "id_anotacao": self.todo.id},
            )
        )

    def test_editar_requires_login(self):
        self._assert_redirects_to_login(
            reverse(
                "main:editar",
                kwargs={"id_user": self.user.id, "id_anotacao": self.todo.id},
            )
        )

    def test_remover_requires_login(self):
        self._assert_redirects_to_login(
            reverse(
                "main:remover",
                kwargs={"id_user": self.user.id, "id_anotacao": self.todo.id},
            )
        )

    def test_folders_requires_login(self):
        self._assert_redirects_to_login(reverse("main:folders"))

    def test_folder_delete_requires_login(self):
        self._assert_redirects_to_login(
            reverse("main:folder_delete", kwargs={"folder_id": self.folder.id})
        )

    def test_folder_edit_requires_login(self):
        self._assert_redirects_to_login(
            reverse("main:folder_edit", kwargs={"folder_id": self.folder.id})
        )


# ==============================================================================
# Testes de Autorização — IDOR em Todo/Anotação
# ==============================================================================


class TodoAuthorizationTests(TestCase):
    """
    Cenários de acesso cruzado entre usuários para Todos (anotações).
    Usuário B nunca deve conseguir ver/editar/excluir objetos de Usuário A.
    """

    def setUp(self):
        self.user_a = make_user("user_a")
        self.user_b = make_user("user_b")
        # Todo privado pertencente ao user_a
        self.todo_a = Todo.objects.create(
            user=self.user_a,
            titulo="Anotação privada de A",
            is_active=True,
        )

    def test_user_b_cannot_view_todo_of_user_a(self):
        """Usuário B não pode visualizar anotação de A (deve receber 403 ou 404)."""
        self.client.force_login(self.user_b)
        url = reverse(
            "main:show",
            kwargs={"id_user": self.user_a.id, "id_anotacao": self.todo_a.id},
        )
        response = self.client.get(url)
        self.assertIn(response.status_code, [403, 404])

    def test_user_b_cannot_edit_todo_of_user_a(self):
        """Usuário B não pode editar anotação de A."""
        self.client.force_login(self.user_b)
        url = reverse(
            "main:editar",
            kwargs={"id_user": self.user_a.id, "id_anotacao": self.todo_a.id},
        )
        response = self.client.post(url, {"titulo": "Hackeado", "anotacao": "mal"})
        self.assertIn(response.status_code, [403, 404])
        # Garante que o título não foi alterado
        self.todo_a.refresh_from_db()
        self.assertEqual(self.todo_a.titulo, "Anotação privada de A")

    def test_user_b_cannot_delete_todo_of_user_a(self):
        """Usuário B não pode excluir anotação de A."""
        self.client.force_login(self.user_b)
        url = reverse(
            "main:remover",
            kwargs={"id_user": self.user_a.id, "id_anotacao": self.todo_a.id},
        )
        response = self.client.post(url)
        self.assertIn(response.status_code, [403, 404])
        # Garante que o todo não foi desativado
        self.todo_a.refresh_from_db()
        self.assertTrue(self.todo_a.is_active)

    def test_user_b_cannot_view_anotacoes_list_of_user_a(self):
        """
        Usuário B acessando /anotacoes/<id_a> deve ver apenas suas próprias anotações,
        nunca as de A (o manager para_usuario filtra por request.user).
        """
        self.client.force_login(self.user_b)
        url = reverse("main:anotacoes", kwargs={"id_user": self.user_a.id})
        response = self.client.get(url)
        # A view responde (200) mas retorna as anotações de B, não de A
        self.assertEqual(response.status_code, 200)
        anotacoes = list(response.context.get("anotacoes", []))
        self.assertNotIn(self.todo_a, anotacoes)

    def test_nonexistent_todo_returns_404(self):
        """ID inexistente deve retornar 404."""
        self.client.force_login(self.user_a)
        url = reverse(
            "main:show",
            kwargs={"id_user": self.user_a.id, "id_anotacao": 99999},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_user_a_can_view_own_todo(self):
        """Usuário A deve conseguir visualizar sua própria anotação."""
        self.client.force_login(self.user_a)
        url = reverse(
            "main:show",
            kwargs={"id_user": self.user_a.id, "id_anotacao": self.todo_a.id},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


# ==============================================================================
# Testes de Autorização — IDOR em Folder
# ==============================================================================


class FolderAuthorizationTests(TestCase):
    """Usuário B não pode editar/excluir pastas de Usuário A."""

    def setUp(self):
        self.user_a = make_user("folder_owner")
        self.user_b = make_user("folder_attacker")
        self.folder_a = Folder.objects.create(user=self.user_a, name="Pasta de A", is_active=True)

    def test_user_b_cannot_delete_folder_of_user_a(self):
        """Usuário B não pode excluir pasta de A."""
        self.client.force_login(self.user_b)
        url = reverse("main:folder_delete", kwargs={"folder_id": self.folder_a.id})
        response = self.client.post(url)
        # get_object_or_404(Folder, id=folder_id, user=request.user) → 404
        self.assertEqual(response.status_code, 404)
        self.folder_a.refresh_from_db()
        self.assertTrue(self.folder_a.is_active)

    def test_user_b_cannot_edit_folder_of_user_a(self):
        """Usuário B não pode editar pasta de A."""
        self.client.force_login(self.user_b)
        url = reverse("main:folder_edit", kwargs={"folder_id": self.folder_a.id})
        response = self.client.post(url, {"name": "Pasta hackeada"})
        self.assertEqual(response.status_code, 404)
        self.folder_a.refresh_from_db()
        self.assertEqual(self.folder_a.name, "Pasta de A")

    def test_user_a_can_delete_own_folder(self):
        """Usuário A pode excluir sua própria pasta."""
        self.client.force_login(self.user_a)
        url = reverse("main:folder_delete", kwargs={"folder_id": self.folder_a.id})
        response = self.client.post(url)
        self.assertIn(response.status_code, [200, 302])


# ==============================================================================
# Testes de Autorização — Agenda
# ==============================================================================


class AgendaAuthorizationTests(TestCase):
    """
    Usuário B não pode ver, cancelar ou editar eventos de Usuário A.
    Estes testes cobrem as correções P0.1 e P0.2.
    """

    def setUp(self):
        self.user_a = make_user("agenda_owner")
        self.user_b = make_user("agenda_attacker")
        from datetime import datetime
        from django.utils import timezone

        self.evento_a = AgendaModel.objects.create(
            user=self.user_a,
            titulo="Evento privado de A",
            dia_do_evento=timezone.now(),
            is_active=True,
        )

    def test_user_b_cannot_view_eventos_of_user_a(self):
        """
        Usuário B acessando /agenda/eventos/<id_a> deve ser redirecionado para login,
        não ver os eventos de A.
        """
        self.client.force_login(self.user_b)
        url = reverse("agenda:eventos", kwargs={"id_user": self.user_a.id})
        response = self.client.get(url)
        # Deve redirecionar para login (id_user não corresponde ao usuário logado)
        self.assertEqual(response.status_code, 302)

    def test_user_b_cannot_view_detalhe_evento_of_user_a(self):
        """Usuário B não pode ver detalhes de evento de A."""
        self.client.force_login(self.user_b)
        url = reverse(
            "agenda:detalhe_sobre_evento",
            kwargs={"id_user": self.user_a.id, "id_evento": self.evento_a.id},
        )
        response = self.client.get(url)
        # Redireciona (id_user não corresponde) ou 404 (evento não pertence ao user_b)
        self.assertIn(response.status_code, [302, 404])

    def test_user_b_cannot_delete_evento_of_user_a(self):
        """Usuário B não pode cancelar evento de A."""
        self.client.force_login(self.user_b)
        url = reverse(
            "agenda:deletar_evento",
            kwargs={"id_user": self.user_a.id, "id_event": self.evento_a.id},
        )
        response = self.client.post(url)
        # Redireciona (id_user não corresponde) ou 404
        self.assertIn(response.status_code, [302, 404])
        # O evento NÃO deve ter sido desativado
        self.evento_a.refresh_from_db()
        self.assertTrue(self.evento_a.is_active)

    def test_user_b_cannot_edit_evento_of_user_a(self):
        """Usuário B não pode editar evento de A."""
        self.client.force_login(self.user_b)
        url = reverse(
            "agenda:editar_evento",
            kwargs={"id_user": self.user_a.id, "id_event": self.evento_a.id},
        )
        response = self.client.post(url, {"titulo": "Evento hackeado"})
        # Redireciona ou 404
        self.assertIn(response.status_code, [302, 404])
        self.evento_a.refresh_from_db()
        self.assertEqual(self.evento_a.titulo, "Evento privado de A")

    def test_user_b_with_known_event_id_cannot_access_event_of_user_a(self):
        """
        Cenário crítico P0.2: Usuário B, mesmo usando id_user=user_b.id e
        id_event=evento_a.id (de A), não consegue acessar o evento de A.
        A correção garante que o evento é filtrado pelo request.user na query.
        """
        self.client.force_login(self.user_b)
        # user_b usa seu próprio id_user mas um id_event que pertence ao user_a
        url = reverse(
            "agenda:deletar_evento",
            kwargs={"id_user": self.user_b.id, "id_event": self.evento_a.id},
        )
        response = self.client.post(url)
        # Deve retornar 404 pois evento não pertence ao user_b
        self.assertEqual(response.status_code, 404)
        self.evento_a.refresh_from_db()
        self.assertTrue(self.evento_a.is_active)

    def test_user_a_can_view_own_eventos(self):
        """Usuário A pode ver seus próprios eventos."""
        self.client.force_login(self.user_a)
        url = reverse("agenda:eventos", kwargs={"id_user": self.user_a.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_user_a_can_delete_own_evento(self):
        """Usuário A pode cancelar seu próprio evento."""
        self.client.force_login(self.user_a)
        url = reverse(
            "agenda:deletar_evento",
            kwargs={"id_user": self.user_a.id, "id_event": self.evento_a.id},
        )
        response = self.client.post(url)
        self.assertIn(response.status_code, [200, 302])
        self.evento_a.refresh_from_db()
        self.assertFalse(self.evento_a.is_active)


# ==============================================================================
# Testes de Autorização — Colaboradores (não deve permitir escalada)
# ==============================================================================


class ColaboradorAuthorizationTests(TestCase):
    """Apenas donos podem gerenciar colaboradores de seus objetos."""

    def setUp(self):
        self.user_a = make_user("colab_owner")
        self.user_b = make_user("colab_attacker")
        self.todo_a = Todo.objects.create(user=self.user_a, titulo="Todo de A", is_active=True)

    def test_user_b_cannot_manage_colaboradores_of_todo_a(self):
        """Usuário B não pode gerenciar colaboradores de um Todo que não é seu."""
        self.client.force_login(self.user_b)
        url = reverse(
            "main:gerenciar_colaboradores",
            kwargs={"tipo": "todo", "pk": self.todo_a.id},
        )
        response = self.client.get(url)
        # get_object_or_404(Todo, pk=pk, user=request.user) → 404
        self.assertEqual(response.status_code, 404)
