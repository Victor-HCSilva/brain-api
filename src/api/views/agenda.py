from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from agenda.models import AgendaModel, Colors, Reminder
from api.permissions.agenda import IsAgendaOwner
from api.serializers.agenda import AgendaModelSerializer, ColorsSerializer
from rest_framework.response import Response
from django.db import transaction
from rest_framework import status


class ColorsViewSet(viewsets.ModelViewSet):
    serializer_class = ColorsSerializer
    permission_classes = [IsAuthenticated, IsAgendaOwner]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Colors.objects.none()
        return Colors.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        if getattr(self, "swagger_fake_view", False) or not request.user.is_authenticated:
            return Response([])
        config, _ = Colors.objects.get_or_create(user=request.user)
        return Response([self.get_serializer(config).data])

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AgendaModelViewSet(viewsets.ModelViewSet):
    serializer_class = AgendaModelSerializer
    permission_classes = [IsAuthenticated, IsAgendaOwner]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return AgendaModel.objects.none()
        return AgendaModel.objects.filter(user=self.request.user, is_active=True)

    def create(self, request, *args, **kwargs):
        # 1. Valida os dados da Agenda usando o serializer padrão
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            # 2. Salva a agenda vinculando o usuário logado
            agenda = serializer.save(user=self.request.user)

            # 3. Cria o Reminder vinculado à agenda recém-criada
            reminder = Reminder.objects.create(
                descricao=agenda.titulo,
                agenda=agenda,  # Passa a instância diretamente
            )

        # 4. Serializa o Reminder (ou monta o dicionário manualmente)
        # Se tiver um ReminderSerializer: reminder_data = ReminderSerializer(reminder).data
        reminder_data = {
            "id": reminder.id,
            "descricao": reminder.descricao,
        }

        # 5. Retorna a resposta customizada
        return Response(
            {"reminder": reminder_data, "evento": serializer.data},
            status=status.HTTP_201_CREATED,
        )
