from ..script import SendEmail
from django.contrib.auth.models import User
import os
from datetime import datetime


def teste():
    u2, _ = User.objects.get_or_create(
        username="person2",
        password="p20--222--",
        defaults={
            "email": os.getenv("TEST_EMAIL_TO"),
        },
    )

    s = SendEmail(to_user=u2, content=f"Teste de envio {datetime.now()}", title="sem titulo")
    s.send()


if __name__ == "__main__":
    teste()
