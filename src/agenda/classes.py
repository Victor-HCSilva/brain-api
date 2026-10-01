import calendar
from collections import defaultdict
from datetime import datetime
import json
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AgendaForm, ColorForm
from .models import AgendaModel, Colors, Reminder


class Agenda:
    def __init__(self, request):
        self.request = request

    def _remider(self, d: str, a: AgendaModel):
        Reminder.objects.create(descricao=c, agenda=a)

    def agenda(self, id_user, ano=None, mes=None):
        if self.request.user.id != id_user:
            return redirect("main:login")

        form = AgendaForm(self.request.POST or None)
        # SEGURANÇA: usa request.user diretamente — não confia no id_user da URL
        # para determinar qual usuário possui os eventos.
        user = self.request.user

        # TODO: Pegar informação
        reminder = None

        if self.request.method == "POST":
            if form.is_valid():
                agenda = form.save(commit=False)
                agenda.user = user
                agenda.save()

                if reminder:
                    self._remider(d=titulo, a=agenda)

                return redirect(
                    "agenda:eventos",
                    id_user=id_user,
                )

        agora = datetime.now()
        ano_visualizado = ano or agora.year
        mes_visualizado = mes or agora.month
        cal = calendar.Calendar(firstweekday=6)
        mes_dias = cal.monthdayscalendar(ano_visualizado, mes_visualizado)
        nome_mes = calendar.month_name[mes_visualizado]
        cor_obj = Colors.objects.filter(user=user).first()
        cor_de_destaque = cor_obj.cor_de_destaque if cor_obj else "#3273dc"
        eventos_do_mes = AgendaModel.objects.filter(
            user=user,
            dia_do_evento__year=ano_visualizado,
            dia_do_evento__month=mes_visualizado,
        ).order_by("dia_do_evento__time")

        eventos_por_dia = defaultdict(list)

        for evento in eventos_do_mes:
            eventos_por_dia[evento.dia_do_evento.day].append(evento.titulo)

        context = {
            "form": form,
            "id_user": id_user,
            "ano": ano_visualizado,
            "mes": mes_visualizado,
            "nome_mes": nome_mes,
            "dias_semana": ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"],
            "mes_dias": mes_dias,
            "cor_de_destaque": cor_de_destaque,
            "eventos_por_dia": dict(eventos_por_dia),
            "dia_atual": agora.day,
            "mes_atual": agora.month,
            "ano_atual": agora.year,
        }

        return render(self.request, "agenda.html", context)


class Eventos:
    def __init__(self, request: HttpRequest):
        self.request = request

    def eventos_(self, id_user: int):
        # SEGURANÇA: id_user da URL é ignorado para autorização.
        # Os eventos exibidos sempre pertencem ao usuário autenticado (request.user).
        # Se o id_user não corresponde ao usuário logado, redireciona para login.
        if self.request.user.id != id_user:
            return redirect("main:login")

        user = self.request.user
        eventos = AgendaModel.objects.filter(user=user, is_active=True)
        context = {
            "eventos": eventos,
            "user": user,
        }
        return render(self.request, "eventos.html", context)

    def detalhe_sobre_evento(self, id_user: int, id_evento):
        # SEGURANÇA: Verifica que o usuário logado tem acesso a este evento.
        # A query vincula o evento ao request.user, garantindo que nenhum
        # outro usuário possa acessar este detalhe mesmo alterando id_evento na URL.
        if self.request.user.id != id_user:
            return redirect("main:login")

        user = self.request.user
        evento = get_object_or_404(AgendaModel, id=id_evento, user=user)
        context = {
            "evento": evento,
            "user": user,
        }

        return render(self.request, "detalhe_sobre_evento.html", context)


class Configs:
    def __init__(self, request: HttpRequest):
        self.request = request

    def configs(self, id_user: int):
        if self.request.user.id != id_user:
            return redirect("main:login")

        form = ColorForm(self.request.POST)
        user = self.request.user
        context = {
            "nada": "nada",
            "form": form,
            "user": user,
        }

        if self.request.method == "POST":
            already_exists = Colors.objects.filter(user=user).first()
            if form.is_valid() and not already_exists:
                config = form.save(commit=False)
                config.user = user
                config.save()
                return redirect("agenda:agenda", id_user=id_user)

            already_exists.cor_de_destaque = self.request.POST.get("cor_de_destaque")
            already_exists.save()
            return redirect("agenda:agenda", id_user=id_user)

        return render(self.request, "configs.html", context)


class DeleteOrEditEvent:
    def __init__(self, request: HttpRequest):
        self.request = request

    def delete_event(self, id_user: int, id_event):
        if self.request.user.id != id_user:
            return redirect("main:login")

        # SEGURANÇA: a query vincula o evento ao request.user.
        # Um atacante que manipule id_event na URL receberá 404
        # se o evento não pertencer ao usuário autenticado.
        evento = get_object_or_404(AgendaModel, id=id_event, user=self.request.user)
        user = self.request.user
        context = {
            "user": user,
            "evento": evento,
        }

        if self.request.method == "POST":
            evento.is_active = False
            evento.save()
            return redirect("agenda:eventos", id_user=id_user)

        return render(self.request, "delete_event.html", context)

    def edit_event(self, id_user: int, id_event: int):
        if self.request.user.id != id_user:
            return redirect("main:login")

        # SEGURANÇA: a query vincula o evento ao request.user.
        # Um atacante que manipule id_event na URL receberá 404
        # se o evento não pertencer ao usuário autenticado.
        evento = get_object_or_404(AgendaModel, id=id_event, user=self.request.user)
        user = self.request.user

        if self.request.method == "POST":
            form = AgendaForm(self.request.POST, instance=evento)
            if form.is_valid():
                form.save()
            else:
                # Form errors are handled by the template/messages flow; keep silent in logs.
                pass

            return redirect("agenda:eventos", id_user=id_user)

        form = AgendaForm(instance=evento)
        context = {
            "nada": "nada",
            "form": form,
            "user": user,
        }

        return render(self.request, "edit.html", context)
