from django.contrib.auth.models import User
from django.db import models

from checklist.configs.colors import COLORS
from core.models.mixins import ActivableAndTimeStamp

MAX_LEGTH = 100


class Tarefa(ActivableAndTimeStamp):
    titulo = models.CharField(max_length=MAX_LEGTH)
    color = models.CharField(max_length=MAX_LEGTH, choices=COLORS, default="black")
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.titulo}"


class Item(ActivableAndTimeStamp):
    # Correção da sintaxe das tuplas de escolhas (choices)
    STATUS_CHOICES = [
        ("nao_iniciado", "⮟ Não Iniciado ⚪"),
        ("fazendo", "⮟ Fazendo ⏳"),
        ("concluido", "⮟ Concluído ✅"),
        ("cancelado", "⮟ Cancelado 🚫"),
    ]

    descricao = models.CharField(max_length=MAX_LEGTH, default="Item da lista")
    feito = models.CharField(max_length=MAX_LEGTH, choices=STATUS_CHOICES, default="nao_iniciado")
    color = models.CharField(max_length=MAX_LEGTH, choices=COLORS, default="black")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="itens")
    tarefa = models.ForeignKey(
        Tarefa, on_delete=models.CASCADE, related_name="itens", blank=True, null=True
    )

    def __str__(self):
        tarefa_titulo = self.tarefa.titulo if self.tarefa else "Sem tarefa"
        return f"{self.descricao} (Tarefa: {tarefa_titulo}) - {self.user.username}"


class Link(ActivableAndTimeStamp):
    url = models.URLField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="links")
    tarefa = models.ForeignKey(
        Tarefa, on_delete=models.CASCADE, related_name="links", blank=True, null=True
    )

    def __str__(self):
        return f"{self.url}"
