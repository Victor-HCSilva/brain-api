from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "main"

urlpatterns = [
    path(
        "login/",
        # Atualizado: template_name agora aponta para "base/login.html"
        views.CustomLoginView.as_view(template_name="base/login.html"),
        name="login",
    ),
    path("home/", views.home, name="home"),
    path("logout/", auth_views.LogoutView.as_view(next_page="main:login"), name="logout"),
    path("main/<int:id_user>", views.create_todo, name="main"),
    path("welcome/<int:id_user>", views.welcome, name="welcome"),
    path("sobre", views.sobre, name="sobre"),
    # ----------------------------------------------------
    path("editar/<int:id_user>/<int:id_anotacao>", views.editar, name="editar"),
    path("remover/<int:id_user>/<int:id_anotacao>", views.remover, name="remover"),
    path("anotacoes/<int:id_user>", views.anotacoes, name="anotacoes"),
    path("show/<int:id_user>/<int:id_anotacao>", views.show, name="show"),
    path(
        "apagar_imagem/<int:id_user>/<int:id_anotacao>/<int:id_imagem>",
        views.apagar_imagem,
        name="apagar_imagem",
    ),
    path(
        "editar_descricao/<int:id_user>/<int:id_anotacao>/<int:id_imagem>",
        views.editar_descricao,
        name="editar_descricao",
    ),
    path("not_found", views.not_found, name="404"),
    path("folders", views.folder_list_create, name="folders"),
    path("folders/<int:folder_id>/delete", views.folder_delete, name="folder_delete"),
    path("folders/<int:folder_id>/update", views.folder_update, name="folder_edit"),
    path("create_account", views.create_account, name="create_account"),
    path(
        "colaboradores/<str:tipo>/<int:pk>/",
        views.gerenciar_colaboradores,
        name="gerenciar_colaboradores",
    ),
    # URLs para gerenciar grupos de colaboração
    path("grupos/", views.listar_grupos, name="listar_grupos"),
    path("grupos/criar/", views.criar_grupo, name="criar_grupo"),
    path("grupos/<int:grupo_id>/editar/", views.editar_grupo, name="editar_grupo"),
    path("grupos/<int:grupo_id>/deletar/", views.deletar_grupo, name="deletar_grupo"),
    path(
        "grupos/<int:grupo_id>/membros/",
        views.gerenciar_membros_grupo,
        name="gerenciar_membros_grupo",
    ),
]
