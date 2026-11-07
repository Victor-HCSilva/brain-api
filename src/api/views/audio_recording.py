from django.db.models import Q
from django.http import FileResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated

from api.serializers.audio_recording import (
    AudioRecordingSerializer,
    LinkerAudioTodoSerializer,
)
from main.models import AudioRecording, LinkerAudioTodo, Todo


AUDIO_CONTENT_TYPES = {
    "aac": "audio/aac",
    "m4a": "audio/mp4",
    "mp3": "audio/mpeg",
    "ogg": "audio/ogg",
    "wav": "audio/wav",
    "webm": "audio/webm",
}


class AudioRecordingViewSet(viewsets.ModelViewSet):
    serializer_class = AudioRecordingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return AudioRecording.objects.none()
        queryset = AudioRecording.objects.filter(is_active=True)
        if self.action in {"retrieve", "stream"}:
            accessible_todos = Todo.objects.para_usuario(user).filter(is_active=True)
            return queryset.filter(
                Q(user=user)
                | Q(vinculos_todo__todo__in=accessible_todos, vinculos_todo__is_active=True)
            ).distinct()
        queryset = queryset.filter(user=user)
        folder_id = self.request.query_params.get("folder")
        if folder_id == "none":
            queryset = queryset.filter(folder__isnull=True)
        elif folder_id is not None:
            if not folder_id.isdigit():
                return queryset.none()
            queryset = queryset.filter(folder_id=int(folder_id))
        return queryset.order_by("-created_at", "-id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        instance.audio.delete(save=False)
        instance.delete()

    @action(detail=True, methods=["get"])
    def stream(self, request, pk=None):
        recording = self.get_object()
        if not recording.audio:
            raise NotFound("Arquivo de áudio não encontrado.")
        extension = recording.audio.name.rsplit(".", 1)[-1].lower()
        content_type = AUDIO_CONTENT_TYPES.get(extension, "application/octet-stream")
        response = FileResponse(
            recording.audio.open("rb"),
            content_type=content_type,
            filename=f"gravacao-{recording.pk}.{recording.audio.name.rsplit('.', 1)[-1]}",
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response


class LinkerAudioTodoViewSet(viewsets.ModelViewSet):
    serializer_class = LinkerAudioTodoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return LinkerAudioTodo.objects.none()
        queryset = LinkerAudioTodo.objects.filter(
            todo__in=Todo.objects.para_usuario(user).filter(is_active=True),
            todo__is_active=True,
            audio__is_active=True,
            is_active=True,
        ).select_related("audio", "todo")
        if self.action in {"retrieve", "update", "partial_update", "destroy"}:
            queryset = queryset.filter(user=user)
        todo_id = self.request.query_params.get("todo")
        if todo_id:
            queryset = queryset.filter(todo_id=todo_id)
        return queryset.order_by("-created_at", "-id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
