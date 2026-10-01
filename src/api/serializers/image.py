from rest_framework import serializers

from main.models import Image, Todo


class ImageSerializer(serializers.ModelSerializer):
    todo = serializers.PrimaryKeyRelatedField(queryset=Todo.objects.all())
    user = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = [
            "id",
            "img",
            "descricao",
            "titulo",
            "data_de_criacao",
            "todo",
            "observacao",
            "user",
        ]
        read_only_fields = ["id", "data_de_criacao", "user"]

    def get_user(self, obj):
        return obj.todo.user_id

    def validate_todo(self, value):
        request = self.context["request"]
        if not value.pode_editar(request.user):
            raise serializers.ValidationError("Você não pode anexar imagem a este Todo.")
        return value
