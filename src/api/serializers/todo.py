from rest_framework import serializers

from api.email.script import send_delay
from main.models import Folder, LinkerTaskTodo, Todo


class FolderSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Folder
        fields = [
            "id",
            "name",
            "user",
            "colaboradores",
            "grupos_colaboracao",
            "is_active",
        ]
        read_only_fields = [
            "id",
            "user",
            "colaboradores",
            "grupos_colaboracao",
            "is_active",
        ]

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["user"] = request.user
        return super().create(validated_data)


class LinkerTaskTodoSerializer(serializers.ModelSerializer):
    """Serializer for LinkerTaskTodo – links a Tarefa (checklist) to a Todo (note)."""

    tarefa_titulo = serializers.SerializerMethodField()
    tarefa_color = serializers.SerializerMethodField()

    class Meta:
        model = LinkerTaskTodo
        fields = ["id", "todo", "tarefa", "tarefa_titulo", "tarefa_color", "is_active"]
        read_only_fields = ["id", "is_active", "tarefa_titulo", "tarefa_color"]

    def get_tarefa_titulo(self, obj) -> str:
        return obj.tarefa.titulo if obj.tarefa else ""

    def get_tarefa_color(self, obj) -> str:
        return obj.tarefa.color if obj.tarefa else ""

    def validate(self, data):
        request = self.context["request"]
        todo = data.get("todo")
        tarefa = data.get("tarefa")
        if todo and todo.user != request.user:
            raise serializers.ValidationError({"todo": "Você não tem permissão para esta tarefa."})
        if tarefa and tarefa.user != request.user:
            raise serializers.ValidationError({"tarefa": "Você não tem permissão para esta lista."})
        return data

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["user"] = request.user
        return super().create(validated_data)


class TodoSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    folder = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.all(), allow_null=True, required=False
    )

    class Meta:
        model = Todo
        fields = [
            "id",
            "user",
            "titulo",
            "favorito",
            "completo",
            "anotacao",
            "prioridade",
            "tag",
            "prazo_inicial",
            "prazo_final",
            "email_notification_at",
            "email_notification_message",
            "email_notification_sent_at",
            "folder",
            "colaboradores",
            "grupos_colaboracao",
            "created_at",
            "updated_at",
            "is_active",
        ]
        read_only_fields = [
            "id",
            "user",
            "colaboradores",
            "grupos_colaboracao",
            "created_at",
            "updated_at",
            "email_notification_sent_at",
            "is_active",
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        mapping = {"1": "Baixa", "2": "Média", "3": "Alta"}
        if rep.get("prioridade") in mapping:
            rep["prioridade"] = mapping[rep["prioridade"]]
        rep["colaboradores_detail"] = [
            {
                "id": u.id,
                "username": u.username,
                "first_name": u.first_name,
                "last_name": u.last_name,
            }
            for u in instance.colaboradores.all()
        ]
        rep["grupos_detail"] = [
            {
                "id": g.id,
                "name": g.name,
                "membros_count": g.membros.count(),
            }
            for g in instance.grupos_colaboracao.filter(is_active=True)
        ]
        return rep

    def validate_folder(self, value):
        request = self.context["request"]
        if value is None:
            return value
        if value.user != request.user and not value.pode_editar(request.user):
            raise serializers.ValidationError("Você não tem permissão para usar esta pasta.")
        return value

    def validate(self, attrs):
        request_user = self.context["request"].user
        notification_fields = ("email_notification_at", "email_notification_message")
        notification_changed = any(field in attrs for field in notification_fields)
        if self.instance and notification_changed and self.instance.user_id != request_user.id:
            raise serializers.ValidationError(
                {"email_notification_at": "Somente o proprietário pode gerenciar esta notificação."}
            )

        notification_owner = self.instance.user if self.instance else request_user
        notification_at = attrs.get(
            "email_notification_at",
            getattr(self.instance, "email_notification_at", None),
        )
        if notification_at and not notification_owner.email:
            raise serializers.ValidationError(
                {"email_notification_at": "Cadastre um e-mail para receber notificações."}
            )
        return attrs

    def update(self, instance, validated_data):
        notification_changed = any(
            field in validated_data and validated_data[field] != getattr(instance, field)
            for field in ("email_notification_at", "email_notification_message")
        )
        if notification_changed:
            validated_data["email_notification_sent_at"] = None
        return super().update(instance, validated_data)

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["user"] = request.user
        username = request.user.username
        t = validated_data.get("titulo", "Titulo não encontrado")
        c = f"{username}, continue assim! Gerencie, estude e registre 📝"
        send_delay.delay(to_user=request.user.id, content=c, title=t)
        return super().create(validated_data)
