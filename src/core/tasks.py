from celery import Celery
from agenda.models import Reminder
from main.models import Todo
from django.contrib.auth.models import User
from django.db.models import F
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone


app = Celery()


@app.task()
def general_status(user_id: int | str):
    user = get_object_or_404(User, id=user_id)
    hoje = timezone.localdate()
    data_limite = hoje + timedelta(days=5)
    tarefas_proximas = Todo.objects.filter(user=user, prazo_final__date__range=(hoje, data_limite))
    tarefas_atrasadas = Todo.objects.filter(user=user, prazo_final__lt=timezone.now())

    return {
        "total_proximas": tarefas_proximas.count(),
        "tarefas_proximas": tarefas_proximas,
        "total_atrasadas": tarefas_atrasadas.count(),
        "tarefas_atrasadas": tarefas_atrasadas,
    }


@app.task()
def reminder(user_id: int | str):
    user = get_object_or_404(User, id=user_id)
    return Reminder.objects.filter(agenda__user=user).values()
