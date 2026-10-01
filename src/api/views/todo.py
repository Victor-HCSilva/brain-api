from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.permissions.todo import IsFolderOwnerOrCollaborator, IsOwnerOrFolderOwner
from api.serializers.group import ShareSerializer
from api.serializers.todo import FolderSerializer, TodoSerializer
from main.models import Folder, Todo


class FolderViewSet(viewsets.ModelViewSet):
    serializer_class = FolderSerializer
    permission_classes = [IsAuthenticated, IsFolderOwnerOrCollaborator]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Folder.objects.none()
        return Folder.objects.filter(
            Q(user=self.request.user)
            | Q(colaboradores=self.request.user)
            | Q(grupos_colaboracao__membros=self.request.user),
            is_active=True,
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post", "delete"], url_path="share")
    def share(self, request, pk=None):
        folder = self.get_object()
        if folder.user != request.user:
            return Response(
                {"detail": "Somente o proprietário pode gerenciar o compartilhamento."},
                status=403,
            )

        serializer = ShareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        users = serializer.validated_data.get("users", [])
        groups = serializer.validated_data.get("groups", [])
        if any(user == request.user for user in users):
            return Response(
                {"detail": "O proprietário não precisa ser compartilhado."},
                status=400,
            )
        if any(group.owner != request.user for group in groups):
            return Response(
                {"detail": "Só é possível compartilhar grupos administrados por você."},
                status=400,
            )

        if request.method == "POST":
            folder.colaboradores.add(*users)
            folder.grupos_colaboracao.add(*groups)
        else:
            folder.colaboradores.remove(*users)
            folder.grupos_colaboracao.remove(*groups)
        return Response(FolderSerializer(folder).data)


class TodoViewSet(viewsets.ModelViewSet):
    serializer_class = TodoSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrFolderOwner]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Todo.objects.none()
        queryset = Todo.objects.para_usuario(self.request.user).filter(is_active=True)
        folder_filter = self.request.query_params.get("folder")

        if folder_filter == "none":
            return queryset.filter(folder__isnull=True)
        if folder_filter is not None:
            if not folder_filter.isdigit():
                return queryset.none()
            return queryset.filter(folder_id=int(folder_filter))
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["patch"], url_path="toggle-complete")
    def toggle_complete(self, request, pk=None):
        todo = self.get_object()
        todo.completo = not todo.completo
        todo.save(update_fields=["completo", "updated_at"])
        serializer = self.get_serializer(todo)
        return Response(serializer.data)

    @action(detail=True, methods=["post", "delete"], url_path="share")
    def share(self, request, pk=None):
        todo = self.get_object()
        if todo.user != request.user:
            return Response(
                {"detail": "Somente o proprietário pode gerenciar o compartilhamento."},
                status=403,
            )

        serializer = ShareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        users = serializer.validated_data.get("users", [])
        groups = serializer.validated_data.get("groups", [])
        if any(user == request.user for user in users):
            return Response(
                {"detail": "O proprietário não precisa ser compartilhado."},
                status=400,
            )
        if any(group.owner != request.user for group in groups):
            return Response(
                {"detail": "Só é possível compartilhar grupos administrados por você."},
                status=400,
            )

        if request.method == "POST":
            todo.colaboradores.add(*users)
            todo.grupos_colaboracao.add(*groups)
        else:
            todo.colaboradores.remove(*users)
            todo.grupos_colaboracao.remove(*groups)
        return Response(TodoSerializer(todo).data)


class LinkerTaskTodoViewSet(viewsets.ModelViewSet):
    """Links between checklist Tarefas and Todos (notes)."""

    from api.serializers.todo import LinkerTaskTodoSerializer as serializer_class

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            from main.models import LinkerTaskTodo

            return LinkerTaskTodo.objects.none()
        from main.models import LinkerTaskTodo

        qs = LinkerTaskTodo.objects.filter(user=self.request.user, is_active=True)
        todo_id = self.request.query_params.get("todo")
        if todo_id:
            qs = qs.filter(todo_id=todo_id)
        return qs

    def get_serializer_class(self):
        from api.serializers.todo import LinkerTaskTodoSerializer

        return LinkerTaskTodoSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
