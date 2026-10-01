from django.conf.global_settings import APPEND_SLASH
import os
import sys
from datetime import timedelta
from pathlib import Path
from celery.schedules import crontab
from dotenv import load_dotenv
from celery.schedules import crontab


CURRENT_FILE = Path(__file__).resolve()

SRC_DIR = CURRENT_FILE.parent.parent

BASE_DIR = SRC_DIR.parent

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

DOTENV_PATH = BASE_DIR / ".envs" / ".env"
load_dotenv(DOTENV_PATH)


def get_env_bool(name: str, default: bool = False) -> bool:
    """Converte valores de variáveis de ambiente para booleano."""
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "t", "yes")

DEBUG = get_env_bool("DEBUG", default=False)
LOGIN_URL = "main:login"
LOGOUT_REDIRECT_URL = "main:create_account"
SECRET_KEY = os.getenv("SECRET_KEY")
REDIS = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-dev-key-substitua-em-producao"
    else:
        raise ValueError("A variável SECRET_KEY precisa estar definida em produção!")

ALLOWED_HOSTS = [url for url in os.getenv("TRUSTED_ORIGINS", "localhost,10.0.0.108").split(',')]
CSRF_TRUSTED_ORIGINS = [
    f"http://{url}" for url in os.getenv("TRUSTED_ORIGINS", "localhost,10.0.0.108").split(',')
]

if not DEBUG and not ALLOWED_HOSTS:
    raise ValueError(
        "A variável ALLOWED_HOSTS precisa estar definida em produção! "
        "Exemplo: ALLOWED_HOSTS=example.com,www.example.com"
    )


if not DEBUG and not CSRF_TRUSTED_ORIGINS:
    raise ValueError(
        "A variável CSRF_TRUSTED_ORIGINS precisa estar definida em produção! "
        "Exemplo: CSRF_TRUSTED_ORIGINS=https://example.com"
    )

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "axes",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_yasg",
]

LOCAL_APPS = [
    "core",
    "api",
    "main",
    "agenda",
    "checklist",
]

INSTALLED_APPS = THIRD_PARTY_APPS + DJANGO_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
    "core.middleware.CurrentUserMiddleware",
]

CORS_ALLOWED_ORIGINS = CSRF_TRUSTED_ORIGINS

ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            SRC_DIR / "main" / "templates",
            BASE_DIR / "templates",  # Diretório global opcional
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "todo_db"),
        "USER": os.environ.get("DB_USER", "todo_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "todo_secret_pass"),
        "HOST": os.environ.get("DB_HOST", "db"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

try:
    import django_redis  # noqa: F401
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": os.getenv("REDIS_LOCATION", "redis://127.0.0.1:6379/1"),
        }
    }
except ImportError:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "default-locmem",
        }
    }

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AXES_FAILURE_LIMIT = 5
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_THRESHOLD_WINDOW = timedelta(hours=24)
AXES_COOLOFF_TIME = timedelta(seconds=200) if DEBUG else timedelta(minutes=30)

SESSION_COOKIE_AGE = 10000 if DEBUG else int(timedelta(minutes=30).total_seconds())
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "api.authentication.FlexibleJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
}

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
        }
    },
    "USE_SESSION_AUTH": False,
}

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CELERY_BROKER_URL = REDIS
CELERY_RESULT_BACKEND = REDIS
CELERY_TIMEZONE = TIME_ZONE

CELERY_BEAT_SCHEDULE = {
    'send-daily-summaries': {
        'task': 'api.tasks.send_summarie_massive',
        'schedule': crontab(hour=6, minute=0),
    },
}

if not DEBUG:
    # Cookies seguros só trafegam via HTTPS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Cookies: declarações explícitas de HttpOnly e SameSite
    # SESSION_COOKIE_HTTPONLY=True é o default do Django, mas declarar explicitamente
    # evita surpresas em atualizações de versão.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"
    # CSRF_COOKIE_HTTPONLY não é ativado pois interfere com o mecanismo CSRF padrão do Django.

    # Security headers de produção
    SECURE_CONTENT_TYPE_NOSNIFF = True  # Bloqueia MIME sniffing pelo navegador
    SECURE_REFERRER_POLICY = "same-origin"  # Não vaza URL para domínios externos
    X_FRAME_OPTIONS = "DENY"  # Previne clickjacking via iframe

    # NOTA: SECURE_HSTS_SECONDS e SECURE_SSL_REDIRECT foram intencionalmente
    # OMITIDOS. Ativar sem confirmar que HTTPS está funcionando e que o
    # reverse proxy (PythonAnywhere) está configurado corretamente pode
    # derrubar o site. Ative manualmente após validação:
    # SECURE_HSTS_SECONDS = 31536000
    # SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # SECURE_HSTS_PRELOAD = True
    # SECURE_SSL_REDIRECT = True

    # Detecção de IP atrás de Proxy Reverso (como PythonAnywhere/Nginx)
    # IMPORTANTE: AXES_PROXY_COUNT=1 pressupõe exatamente 1 proxy confiável (PythonAnywhere)
    # entre o cliente e o Django. Se a infraestrutura mudar, revisar este valor.
    # Não confiar cegamente em X-Forwarded-For se a aplicação puder ser acessada diretamente.
    AXES_PROXY_COUNT = 1
    AXES_META_PRECEDENCE_ORDER = (
        "HTTP_X_FORWARDED_FOR",
        "REMOTE_ADDR",
    )
