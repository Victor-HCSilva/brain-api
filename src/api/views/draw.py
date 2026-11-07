from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from api.serializers.draw import DrawDocumentSerializer, LinkerDrawTodoSerializer
from main.models import DrawDocument, LinkerDrawTodo, Todo


class DrawDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DrawDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return DrawDocument.objects.none()
        queryset = DrawDocument.objects.filter(user=user, is_active=True)
        folder_id = self.request.query_params.get("folder")
        if folder_id == "none":
            queryset = queryset.filter(folder__isnull=True)
        elif folder_id is not None:
            if not folder_id.isdigit():
                return queryset.none()
            queryset = queryset.filter(folder_id=int(folder_id))
        return queryset.order_by("-updated_at", "-id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class LinkerDrawTodoViewSet(viewsets.ModelViewSet):
    serializer_class = LinkerDrawTodoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return LinkerDrawTodo.objects.none()
        queryset = LinkerDrawTodo.objects.filter(
            todo__in=Todo.objects.para_usuario(user).filter(is_active=True),
            todo__is_active=True,
            drawing__is_active=True,
            is_active=True,
        ).select_related("todo", "drawing")
        if self.action in {"retrieve", "update", "partial_update", "destroy"}:
            queryset = queryset.filter(user=user)
        todo_id = self.request.query_params.get("todo")
        drawing_id = self.request.query_params.get("drawing")
        if todo_id:
            queryset = queryset.filter(todo_id=todo_id)
        if drawing_id:
            queryset = queryset.filter(drawing_id=drawing_id)
        return queryset.order_by("-created_at", "-id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
