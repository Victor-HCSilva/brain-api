from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from api.views.agenda import AgendaModelViewSet, ColorsViewSet
from api.views.auth import MeView, RegisterView
from api.views.audio_recording import AudioRecordingViewSet, LinkerAudioTodoViewSet
from api.views.draw import DrawDocumentViewSet, LinkerDrawTodoViewSet
from api.views.checklist import ItemViewSet, LinkViewSet, TarefaViewSet
from api.views.group import GroupViewSet
from api.views.image import ImageViewSet
from api.views.notification import ScheduledEmailNotificationViewSet
from api.views.search import GlobalSearchView
from api.views.todo import FolderViewSet, LinkerTaskTodoViewSet, TodoViewSet
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

app_name = "api"

schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
        default_version="v1",
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

router = DefaultRouter()
router.register(r"todos", TodoViewSet, basename="todo")
router.register(r"folders", FolderViewSet, basename="folder")
router.register(r"groups", GroupViewSet, basename="group")
router.register(r"checklist/tarefas", TarefaViewSet, basename="tarefa")
router.register(r"checklist/itens", ItemViewSet, basename="item")
router.register(r"checklist/links", LinkViewSet, basename="link")
router.register(r"agenda/configs", ColorsViewSet, basename="colors")
router.register(r"agenda", AgendaModelViewSet, basename="agenda")
router.register(r"images", ImageViewSet, basename="image")
router.register(r"notifications", ScheduledEmailNotificationViewSet, basename="notification")
router.register(r"audio-recordings", AudioRecordingViewSet, basename="audio-recording")
router.register(r"audio-linkers", LinkerAudioTodoViewSet, basename="audio-linker")
router.register(r"drawings", DrawDocumentViewSet, basename="drawing")
router.register(r"draw-linkers", LinkerDrawTodoViewSet, basename="draw-linker")
router.register(r"linkers", LinkerTaskTodoViewSet, basename="linker")


urlpatterns = [
    path("swagger<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    path(
        "auth/",
        include(
            [
                path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
                path("register/", RegisterView.as_view(), name="register"),
                path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
                path("me/", MeView.as_view(), name="me"),
            ]
        ),
    ),
    path("search/", GlobalSearchView.as_view(), name="search"),
    path("", include(router.urls)),
]
