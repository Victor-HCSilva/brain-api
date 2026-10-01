from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from core.models.mixins import ActivableAndTimeStamp


# Cor de destaque
class Colors(ActivableAndTimeStamp):
    # OneToOneField garante que cada usuário tenha apenas uma configuração
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,  # Torna o usuário a chave primária da tabela
    )
    cor_de_destaque = models.CharField("Cor de destaque", max_length=50, default="#3b82f6")
    cor_do_dia = models.CharField("Cor do dia", max_length=50, default="#3b82f6")

    def __str__(self):
        return f"Configuração de {self.user.username}"


# Agenda
class AgendaModel(ActivableAndTimeStamp):
    PRIORIDADES = [
        ("1", "Mínima"),
        ("2", "Mediana"),
        ("3", "Máxima"),
    ]
    TIPOS_DE_EVENTO = [
        ("Prova", "Prova"),
        ("Atividade", "Atividade"),
        ("Terefa", "Tarefa"),
        ("Importante", "Importante"),
        ("Lembrete", "Lembrete"),
        ("Outro", "Outro"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuário")
    titulo = models.CharField("Título", max_length=100, default="Sem titulo")
    descricao = models.TextField("Descrição", blank=True, default="Sem descrição", max_length=100)
    tipo_de_evento = models.CharField(
        "Tipo de Evento",
        max_length=100,
        choices=TIPOS_DE_EVENTO,
        default=TIPOS_DE_EVENTO[4][0],
    )
    importancia = models.CharField(
        "Importância",
        max_length=100,
        choices=PRIORIDADES,
        default=PRIORIDADES[0][0],
    )
    dia_do_evento = models.DateTimeField("Data do evento", default=timezone.now)

    class Meta:
        ordering = ["dia_do_evento"]

    def __str__(self):
        return f"{self.titulo} ({self.user.username}) - {self.dia_do_evento.strftime('%d/%m/%Y')}"


class Reminder(ActivableAndTimeStamp):
    descricao = models.TextField("Descrição", blank=True, default="Sem descrição", max_length=100)
    agenda = models.ForeignKey(
        AgendaModel, on_delete=models.CASCADE, verbose_name="Registro da agenda"
    )

    def __str__(self):
        return f"{self.agenda.titulo}"
