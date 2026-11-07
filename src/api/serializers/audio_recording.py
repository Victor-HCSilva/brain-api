import os

from django.urls import reverse
from rest_framework import serializers

from main.models import AudioRecording, Folder, LinkerAudioTodo, Todo


ALLOWED_AUDIO_EXTENSIONS = {"aac", "m4a", "mp3", "ogg", "wav", "webm"}
MAX_AUDIO_SIZE = 25 * 1024 * 1024


class AudioRecordingSerializer(serializers.ModelSerializer):
    audio = serializers.FileField(write_only=True, required=False)
    folder = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.filter(is_active=True), allow_null=True, required=False
    )
    folder_name = serializers.CharField(source="folder.name", read_only=True, allow_null=True)
    stream_url = serializers.SerializerMethodField()

    class Meta:
        model = AudioRecording
        fields = ["id", "titulo", "audio", "folder", "folder_name", "stream_url", "created_at"]
        read_only_fields = ["id", "stream_url", "created_at"]

    def get_stream_url(self, obj):
        return reverse("api:audio-recording-stream", kwargs={"pk": obj.pk})

    def validate_audio(self, value):
        extension = os.path.splitext(value.name)[1].lower().lstrip(".")
        if extension not in ALLOWED_AUDIO_EXTENSIONS:
            raise serializers.ValidationError(
                "Formato de áudio não suportado. Use AAC, M4A, MP3, OGG, WAV ou WEBM."
            )
        if value.size > MAX_AUDIO_SIZE:
            raise serializers.ValidationError("O áudio deve ter no máximo 25 MB.")
        return value

    def validate_titulo(self, value):
        titulo = value.strip()
        if not titulo:
            raise serializers.ValidationError("Informe um título para a gravação.")
        return titulo

    def validate_folder(self, value):
        if value is not None and not value.pode_editar(self.context["request"].user):
            raise serializers.ValidationError("Você não tem permissão para usar esta pasta.")
        return value

    def validate(self, attrs):
        if not self.instance and not attrs.get("audio"):
            raise serializers.ValidationError({"audio": "Selecione um arquivo de áudio."})
        return attrs


class LinkerAudioTodoSerializer(serializers.ModelSerializer):
    audio_titulo = serializers.CharField(source="audio.titulo", read_only=True)
    audio_stream_url = serializers.SerializerMethodField()
    todo_titulo = serializers.CharField(source="todo.titulo", read_only=True)

    class Meta:
        model = LinkerAudioTodo
        fields = [
            "id",
            "todo",
            "todo_titulo",
            "audio",
            "audio_titulo",
            "audio_stream_url",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "todo_titulo",
            "audio_titulo",
            "audio_stream_url",
            "created_at",
        ]

    def get_audio_stream_url(self, obj):
        return reverse("api:audio-recording-stream", kwargs={"pk": obj.audio_id})

    def validate(self, attrs):
        request = self.context["request"]
        todo = attrs.get("todo")
        audio = attrs.get("audio")
        if todo and not todo.pode_editar(request.user):
            raise serializers.ValidationError(
                {"todo": "Você não tem permissão para vincular áudio a esta tarefa."}
            )
        if audio and audio.user_id != request.user.id:
            raise serializers.ValidationError(
                {"audio": "Você só pode vincular gravações da sua biblioteca."}
            )
        if todo and audio and LinkerAudioTodo.objects.filter(
            todo=todo, audio=audio, user=request.user, is_active=True
        ).exists():
            raise serializers.ValidationError(
                {"audio": "Esta gravação já está vinculada à tarefa."}
            )
        return attrs
