from django.shortcuts import get_object_or_404
from django.db import models
import smtplib
from logging import getLogger
import os
from django.contrib.auth.models import User
from email.message import EmailMessage
from api.models import DispatchLog
from django.core.cache import cache
from django.core.management.utils import get_random_secret_key
from time import sleep

logger = getLogger("__main__")

try:
    from celery import shared_task
except ImportError:

    def shared_task(func):
        class DummyTask:
            def __init__(self, fn):
                self.fn = fn

            def __call__(self, *args, **kwargs):
                return self.fn(*args, **kwargs)

            def delay(self, *args, **kwargs):
                return self.fn(*args, **kwargs)

        return DummyTask(func)


class SendEmail:
    timeout = 5  # 5s
    server_type = os.getenv("SERVER_TYPE")
    port = os.getenv("EMAIL_PORT")
    link = os.getenv("LINK_PAGINA")
    email = os.getenv("EMAIL_SYSTEM")
    password = os.getenv("EMAIL_PASSWORD")
    success = "OK"
    failure = "FAIL"

    def __init__(self, to_user: User, content: str, title: str, time=3) -> None:
        self.to_user = to_user
        self.content = content
        self.title = title
        self.time = time

    def _idempotency(self, smtp, msg: EmailMessage, time=3) -> None:
        if time == 0 or cache.get(self.to_user.email) == self.success:
            return

        try:
            sleep(1)
            err = smtp.send_message(msg)

            if err and cache.get(self.to_user.email) != self.success:
                cache.set(self.to_user.email, self.failure)
                return self._idempotency(smtp, msg, time - 1)

            return cache.set(self.to_user.email, self.success, self.timeout)

        except (smtplib.SMTPException, Exception) as e:
            err = True

    def _template(self, username: str, content: str):
        return f"""
		<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 480px; margin: 20px auto; padding: 32px 24px 20px 24px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
    
    <!-- Título / Saudação -->
    <h1 style="margin: 0 0 20px 0; font-size: 22px; font-weight: 600; color: #0f172a; text-align: center;">
        Olá, {username}!
    </h1>

    <!-- Card de Conteúdo -->
    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px 16px; text-align: center;">
        
        <!-- Badge / Notificação -->
        <span style="display: inline-block; padding: 4px 12px; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #0f766e; background-color: #ccfbf1; border-radius: 9999px; margin-bottom: 14px;">
            Sua notificação
        </span>

        <!-- Mensagem de Conteúdo -->
        <p style="margin: 0 0 20px 0; font-size: 15px; line-height: 1.6; color: #475569;">
            {content}
        </p>

        <!-- Botão de Ação -->
        <a href="{self.link}" target="_blank" style="display: inline-block; background-color: #0f766e; color: #ffffff; text-decoration: none; padding: 10px 22px; font-size: 14px; font-weight: 500; border-radius: 6px;">
            Visite a página
        </a>
    </div>

    <!-- Footer / Rodapé -->
    <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #f1f5f9; text-align: center;">
        <p style="margin: 0; font-size: 12px; color: #94a3b8; line-height: 1.5;">
            🧠 <strong>Equipe Brain</strong> &bull; &copy; 2026 Todos os direitos reservados.
        </p>
    </div>

</div>
		"""

    def send(self):
        try:
            if not self.to_user.email or not self.email:
                logger.info(f"Usuário: {self.to_user.email}\nSistema: {self.email}")
                raise ValueError("Algum erro ocorreu ao buscar emails")

            from_ = self.email
            msg = EmailMessage()
            msg["Subject"] = self.title
            msg["From"] = from_
            msg["To"] = self.to_user.email
            msg.set_content(
                self._template(content=self.content, username=self.to_user.username),
                subtype="html",
            )

            with smtplib.SMTP(self.server_type, self.port) as smtp:
                smtp.starttls()
                smtp.login(from_, self.password)
                self._idempotency(smtp, msg, self.time)

                obj = DispatchLog.objects.create(
                    to=self.to_user, title=self.title, content=self.content
                )
                logger.info(f"E-mail de {from_} para {self.to_user.email} enviado com sucesso!")

        except Exception as e:
            logger.info(f"Erro ao enviar o email: {e}")


@shared_task
def send_delay(to_user: int | str, content: str, title: str, time=3):
    user = get_object_or_404(User, id=to_user)
    s = SendEmail(user, content, title, time)
    s.send()
