from django.db import models
from core.models.mixins import ActivableAndTimeStamp
from django.contrib.auth.models import User


class DispatchLog(ActivableAndTimeStamp):
    to = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enviado_para")
    title = models.CharField(max_length=100)
    content = models.TextField(max_length=15000)

    def __str__(self):
        return f"De {self.sent_from.username} para {self.to.username} em {self.created_at}"
