from django.contrib.auth import get_user_model
from rest_framework import serializers

from main.models import CollaborationGroup

User = get_user_model()


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]


class GroupSerializer(serializers.ModelSerializer):
    owner = UserSummarySerializer(read_only=True)
    membros = UserSummarySerializer(many=True, read_only=True)

    class Meta:
        model = CollaborationGroup
        fields = [
            "id",
            "name",
            "descricao",
            "owner",
            "membros",
            "created_at",
            "updated_at",
            "is_active",
        ]
        read_only_fields = [
            "id",
            "owner",
            "membros",
            "created_at",
            "updated_at",
            "is_active",
        ]


class GroupMemberSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=False, allow_null=True)
    username = serializers.CharField(required=False, allow_null=True)
    user = serializers.CharField(required=False, allow_null=True)

    def validate(self, attrs):
        user_val = attrs.get("user") or attrs.get("username") or attrs.get("user_id")
        if not user_val:
            raise serializers.ValidationError(
                {"detail": "Informe o nome de usuário ou o ID do colaborador."}
            )

        user = None
        user_str = str(user_val).strip()

        # 1. If numeric string or integer, check by ID first
        if user_str.isdigit():
            user = User.objects.filter(pk=int(user_str)).first()

        # 2. Fallback or primary lookup by username (case-insensitive)
        if user is None:
            user = User.objects.filter(username__iexact=user_str).first()

        if user is None:
            raise serializers.ValidationError(
                {"detail": f"Usuário '{user_str}' não foi encontrado."}
            )

        attrs["user"] = user
        return attrs


class ShareSerializer(serializers.Serializer):
    user_ids = serializers.ListField(child=serializers.CharField(), required=False)
    group_ids = serializers.PrimaryKeyRelatedField(
        source="groups",
        queryset=CollaborationGroup.objects.filter(is_active=True),
        many=True,
        required=False,
    )

    def validate(self, attrs):
        raw_user_ids = attrs.get("user_ids", [])
        users = []
        for val in raw_user_ids:
            u_str = str(val).strip()
            u = None
            if u_str.isdigit():
                u = User.objects.filter(pk=int(u_str)).first()
            if u is None:
                u = User.objects.filter(username__iexact=u_str).first()
            if u is None:
                raise serializers.ValidationError(
                    {"detail": f"Usuário '{u_str}' não foi encontrado."}
                )
            users.append(u)
        attrs["users"] = users

        if not attrs.get("users") and not attrs.get("groups"):
            raise serializers.ValidationError("Informe ao menos um usuário ou grupo.")
        return attrs
