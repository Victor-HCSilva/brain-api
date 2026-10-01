from typing import Any
from celery import shared_task
from django.contrib.auth.models import User
from api.email.script import send_delay
from logging import getLogger
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from main.models import Todo
from api.email.script import SendEmail


logger = getLogger("__name__")


class Summarie:
    def __init__(self) -> None:
        return

    def send_todos_summarie(self, user: User) -> None:
        """
        Envia um resumo de anotações para email
        Args:
            user: User
        Returns:
            None
        """
        hoje = timezone.localdate()
        data_limite = hoje + timedelta(days=5)
        tarefas_proximas = Todo.objects.filter(
            user=user, prazo_final__date__range=(hoje, data_limite), is_active=True
        ).values("titulo", "prazo_final")

        tarefas_atrasadas = Todo.objects.filter(
            user=user, prazo_final__lt=timezone.now(), is_active=True
        ).values("titulo", "prazo_final")

        # Formatação das tarefas próximas (com borda neutra e destaque de prazo)
        tarefas_proximas_f = "".join(
            [
                f"""
                <li style="padding: 10px 14px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; margin-bottom: 8px; list-style: none; text-align: left;">
                    <div style="font-size: 14px; font-weight: 600; color: #1e293b;">{t.get("titulo", "-")}</div>
                    <div style="font-size: 12px; color: #64748b; margin-top: 2px;">Prazo final: {t.get("prazo_final", "-")}</div>
                </li>
                """
                for t in tarefas_proximas
            ]
        ) or (
            '<li style="padding: 12px; background-color: #ffffff; border: 1px dashed'
            " #cbd5e1; border-radius: 6px; color: #94a3b8; font-size: 13px;"
            ' text-align: center; list-style: none;">Nenhuma tarefa próxima</li>'
        )

        # Formatação das tarefas atrasadas (com tom avermelhado)
        tarefas_atrasadas_f = "".join(
            [
                f"""
                <li style="padding: 10px 14px; background-color: #fff5f5; border: 1px solid #fecaca; border-radius: 6px; margin-bottom: 8px; list-style: none; text-align: left;">
                    <div style="font-size: 14px; font-weight: 600; color: #991b1b;">{t.get("titulo", "-")}</div>
                    <div style="font-size: 12px; color: #b91c1c; margin-top: 2px;">Venceu em: {t.get("prazo_final", "-")}</div>
                </li>
                """
                for t in tarefas_atrasadas
            ]
        ) or (
            '<li style="padding: 12px; background-color: #ffffff; border: 1px dashed'
            " #cbd5e1; border-radius: 6px; color: #94a3b8; font-size: 13px;"
            ' text-align: center; list-style: none;">Nenhuma tarefa em atraso</li>'
        )
        formated_status_content = f""" 
            <!-- Saudação -->
           
            <!-- SEÇÃO: Tarefas Atrasadas -->
            <div style="background-color: #fef2f2; border: 1px solid #fee2e2; border-radius: 8px; padding: 18px 16px; margin-bottom: 20px;">
                <div style="margin-bottom: 12px;">
                    <span style="display: inline-block; padding: 4px 10px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #991b1b; background-color: #fee2e2; border-radius: 9999px;">
                        ⚠️ Tarefas Atrasadas
                    </span>
                </div>
                
                <ul style="margin: 0; padding: 0;">
                    {tarefas_atrasadas_f}
                </ul>
            </div>

            <!-- SEÇÃO: Tarefas Próximas -->
            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px 16px; margin-bottom: 24px;">
                <div style="margin-bottom: 12px;">
                    <span style="display: inline-block; padding: 4px 10px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #0f766e; background-color: #ccfbf1; border-radius: 9999px;">
                        📅 Próximos 5 Dias
                    </span>
                </div>

                <ul style="margin: 0; padding: 0;">
                    {tarefas_proximas_f}
                </ul>
            </div>
       
        """
        s = SendEmail(user, formated_status_content, "Seu resumo completo", 3)
        s.send()


@shared_task
def _send_summarie(user_id: int | str):
    """
    Envia resumo de anotações a um usuário.
    Args:
        filters: dict[str, Any]
    Returns:
        None
    """
    try:
        user = User.objects.filter(id=user_id).first()
        s = Summarie()
        s.send_todos_summarie(user)
    except Exception as e:
        logger.info(f"Erro ocorrido ao tentar enviar emails: {e}")


@shared_task
def send_summarie_massive(filters={"is_active": True}):  #
    """Envio a resumos de anotações para cada usuário"""
    ids = User.objects.filter(**filters).values_list("id", flat=True)
    for user_id in ids:
        _send_summarie.delay(user_id)
