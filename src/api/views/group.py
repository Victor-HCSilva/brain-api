from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.permissions.group import IsGroupManager
from api.serializers.group import GroupMemberSerializer, GroupSerializer
from main.models import CollaborationGroup

User = get_user_model()


class GroupViewSet(viewsets.ModelViewSet):
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, IsGroupManager]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return CollaborationGroup.objects.none()
        return (
            CollaborationGroup.objects.filter(
                is_active=True,
            )
            .filter(owner=self.request.user)
            .distinct()
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    @action(detail=True, methods=["get", "post"], url_path="members")
    def add_member(self, request, pk=None):
        group = self.get_object()
        if request.method == "GET":
            return Response(
                {"members": GroupSerializer(group).data["membros"]},
                status=status.HTTP_200_OK,
            )

        serializer = GroupMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        if user == group.owner:
            return Response(
                {"detail": "O proprietário não pode ser membro do próprio grupo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        group.adicionar_membro(user)
        return Response(self.get_serializer(group).data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"members/(?P<user_id>[^/]+)",
    )
    def remove_member(self, request, pk=None, user_id=None):
        group = self.get_object()
        user = None
        user_str = str(user_id).strip()
        if user_str.isdigit():
            user = User.objects.filter(pk=int(user_str)).first()
        if user is None:
            user = User.objects.filter(username__iexact=user_str).first()

        if user is None:
            return Response(
                {"detail": "Usuário não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        group.remover_membro(user)
        return Response(status=status.HTTP_204_NO_CONTENT)
