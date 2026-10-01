from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.dateparse import parse_date

from agenda.models import Colors
from main.forms import (
    AddColaboradorForm,
    CollaborationGroupForm,
    FolderForm,
    ImageForm,
    LinkerTaskTodoForm,
    TodoForm,
    UserForm,
)
from main.models import CollaborationGroup, Folder, Image, LinkerTaskTodo, Todo
from main.utils import (
    get_label,
)


@login_required
def anotacoes(request, id_user):
    # LÓGICA DE COLABORAÇÃO:
    # Um usuário pode ver suas próprias anotações OU anotações de outros onde ele é colaborador.
    # Por isso, não redirecionamos mais apenas pelo ID da URL.

    # Coleta a pasta selecionada na URL (?folder=ID)
    selected_folder = request.GET.get("folder", None)
    if selected_folder and selected_folder.isdigit():
        selected_folder = int(selected_folder)
    else:
        selected_folder = None

    # Usamos o manager customizado 'para_usuario' que criamos nos Models
    base_queryset = Todo.objects.para_usuario(request.user).filter(is_active=True)

    # Filtros de busca
    filters = {}
    if selected_folder:
        filters["folder_id"] = selected_folder

        # Filtros condicionais (dentro da pasta)
        if request.GET.get("tag"):
            filters["tag"] = request.GET.get("tag")
        if request.GET.get("prioridade"):
            filters["prioridade"] = get_label(request.GET.get("prioridade"))
        if request.GET.get("favorito") == "true":
            filters["favorito"] = True
        if request.GET.get("completo") == "true":
            filters["completo"] = True
        if request.GET.get("titulo"):
            filters["titulo__icontains"] = request.GET.get("titulo")

        prazo_inicial: str = request.GET.get("prazo_inicial", "")
        prazo_final = request.GET.get("prazo_final", "")

        # if prazo_final is not None:
        #     filters["prazo_inicial__gte"] = parse_date(prazo_inicial)

        # if prazo_final is not None:
        #     filters["prazo_final__lte"] = parse_date(prazo_final)
    else:
        # Se não houver pasta, mostra os que não tem pasta vinculada
        filters["folder_id__isnull"] = True

    # Aplica os filtros ao queryset base que já respeita a colaboração
    todos = base_queryset.filter(**filters).order_by("-id")

    # Busca as pastas onde o usuário é dono OU colaborador
    folders = Folder.objects.filter(
        Q(user=request.user) | Q(colaboradores=request.user), is_active=True
    ).distinct()

    # Cor de destaque (sempre baseada no usuário logado)
    cor_obj = Colors.objects.filter(user=request.user).first()
    cor_de_destaque = cor_obj.cor_de_destaque if cor_obj else "#3273dc"

    context = {
        "anotacoes": todos,
        "folders": folders,
        "all_tags": Todo.TAGS,
        "all_prioridades": Todo.PRIORIDADES,
        "selected_folder": selected_folder,
        "selected_tag": request.GET.get("tag", ""),
        "selected_prioridade": request.GET.get("prioridade", ""),
        "selected_favorito": request.GET.get("favorito", ""),
        "selected_completo": request.GET.get("completo", ""),
        "selected_titulo": request.GET.get("titulo", ""),
        "prazo_inicial": request.GET.get("prazo_inicial", ""),
        "prazo_final": request.GET.get("prazo_final", ""),
        "cor_de_destaque": cor_de_destaque,
        "id_user": id_user,  # Mantido para compatibilidade de URL no template
    }
    return render(request, "todo/anotacoes.html", context)


@login_required()
def show(request, id_user, id_anotacao):
    # Busca a tarefa, mas verifica se o usuário logado tem acesso a ela
    task = get_object_or_404(Todo, id=id_anotacao)

    # SEGURANÇA: Se não for dono e não for colaborador, bloqueia
    if not task.pode_editar(request.user):
        return HttpResponseForbidden("Você não tem permissão para visualizar esta anotação.")

    img_form = ImageForm()
    # O user aqui deve ser o logado para filtrar os checklists DELE
    task_form = LinkerTaskTodoForm(user=request.user)

    if request.method == "POST":
        if "submit_image" in request.POST:
            img_form = ImageForm(request.POST, request.FILES)
            if img_form.is_valid():
                image = img_form.save(commit=False)
                image.todo = task  # Vincula ao todo pai
                image.save()
                return redirect("main:show", id_user=id_user, id_anotacao=id_anotacao)

        elif "submit_linker_task" in request.POST:
            task_form = LinkerTaskTodoForm(request.POST, user=request.user)
            if task_form.is_valid():
                linker = task_form.save(commit=False)
                linker.user = request.user
                linker.todo = task

                vinculo_ja_existe = LinkerTaskTodo.objects.filter(
                    tarefa=linker.tarefa,
                    todo=linker.todo,
                    is_active=True,
                ).exists()

                if not vinculo_ja_existe:
                    linker.save()
                    messages.success(request, "Checklist vinculado com sucesso!")
                else:
                    messages.error(request, "Este checklist já está vinculado.")

                return redirect("main:show", id_user=id_user, id_anotacao=id_anotacao)

    tarefas_vinculadas = LinkerTaskTodo.objects.filter(todo=task, is_active=True).select_related(
        "tarefa"
    )

    # Corrigido para usar a relação 'imagens' definida no model
    imgs = task.imagens.all()

    context = {
        "tarefa": task,
        "user": request.user,
        "img_form": img_form,
        "imagens": imgs,
        "task_form": task_form,
        "tarefas_vinculadas": tarefas_vinculadas,
    }
    return render(request, "todo/show.html", context)


@login_required()
def editar(request, id_user, id_anotacao):
    todo = get_object_or_404(Todo, id=id_anotacao)

    if not todo.pode_editar(request.user):
        return HttpResponseForbidden("Sem permissão para editar.")

    if request.method == "POST":
        form = TodoForm(request.POST, instance=todo)
        if form.is_valid():
            form.save()
            return redirect("main:show", id_user=id_user, id_anotacao=todo.id)
    else:
        form = TodoForm(instance=todo)

    context = {
        "user": request.user,
        "form": form,
        "tarefa": todo,
    }
    return render(request, "todo/editar.html", context)


@login_required()
def remover(request, id_user, id_anotacao):
    todo = get_object_or_404(Todo, id=id_anotacao)

    # APENAS O DONO ou o DONO DA PASTA pode remover
    if not todo.pode_excluir(request.user):
        return HttpResponseForbidden("Apenas o proprietário pode excluir esta anotação.")

    if request.method == "POST":
        todo.is_active = False
        todo.save()
        # SEGURANÇA: usa request.user.id para o redirect — não confia no id_user da URL.
        return redirect("main:anotacoes", id_user=request.user.id)

    return render(request, "todo/delete.html", {"user": request.user, "tarefa": todo})


@login_required()
def apagar_imagem(request, id_user, id_imagem, id_anotacao):
    image = get_object_or_404(Image, id=id_imagem)
    todo = get_object_or_404(Todo, id=id_anotacao)

    if not todo.pode_editar(request.user):
        return HttpResponseForbidden("Sem permissão.")

    if request.method == "POST":
        image.delete()
        return redirect("main:show", id_user=id_user, id_anotacao=id_anotacao)

    return render(
        request,
        "todo/apagar_imagem.html",
        {"user": request.user, "imagem": image, "tarefa": todo},
    )


@login_required()
def editar_descricao(request, id_user, id_imagem, id_anotacao):
    image = get_object_or_404(Image, id=id_imagem)
    todo = get_object_or_404(Todo, id=id_anotacao)

    if not todo.pode_editar(request.user):
        return HttpResponseForbidden()

    if request.method == "POST":
        form = ImageForm(request.POST, request.FILES, instance=image)
        if form.is_valid():
            form.save()
            return redirect("main:show", id_user=id_user, id_anotacao=id_anotacao)
    else:
        form = ImageForm(instance=image)

    return render(
        request,
        "todo/editar_descricao.html",
        {"user": request.user, "imagem": image, "tarefa": todo, "form": form},
    )


@login_required
def folder_update(request, folder_id):
    # Apenas o dono da pasta pode mudar o nome ou configurações dela
    folder = get_object_or_404(Folder, id=folder_id, user=request.user, is_active=True)

    if request.method == "POST":
        form = FolderForm(request.POST, instance=folder)
        if form.is_valid():
            form.save()
            messages.success(request, "Pasta atualizada!")
            return redirect("main:folders")
    else:
        form = FolderForm(instance=folder)

    return render(request, "folders/folder_edit.html", {"form": form, "folder": folder})


@login_required
def folder_delete(request, folder_id):
    folder = get_object_or_404(Folder, id=folder_id, user=request.user, is_active=True)
    if request.method == "POST":
        folder.is_active = False
        folder.save()
        messages.success(request, f"Pasta '{folder.name}' removida.")
    return redirect("main:folders")


@login_required()
def create_todo(request, id_user: int):
    # Garantir que o usuário só crie coisas para ele mesmo, mas possa escolher pastas compartilhadas
    if request.user.id != id_user:
        return redirect("main:anotacoes", id_user=request.user.id)

    if request.method == "POST":
        form = TodoForm(request.POST)
        if form.is_valid():
            todo = form.save(commit=False)
            todo.user = request.user
            todo.save()
            form.save_m2m()  # Importante para salvar colaboradores se houver no form
            return redirect("main:anotacoes", id_user=request.user.id)
    else:
        form = TodoForm()

    # Filtra pastas onde ele pode colocar anotações (dele ou compartilhadas com ele)
    folders = Folder.objects.filter(
        Q(user=request.user) | Q(colaboradores=request.user), is_active=True
    ).distinct()

    context = {
        "username": request.user.username.title(),
        "form": form,
        "folders": folders,
    }
    return render(request, "base/main.html", context)


@login_required
def folder_list_create(request):
    # Lista pastas dele + pastas onde é colaborador
    folders = Folder.objects.filter(
        Q(user=request.user) | Q(colaboradores=request.user), is_active=True
    ).distinct()

    if request.method == "POST":
        form = FolderForm(request.POST)
        if form.is_valid():
            folder = form.save(commit=False)
            folder.user = request.user
            folder.save()
            messages.success(request, "Pasta criada!")
            return redirect("main:folders")
    else:
        form = FolderForm()

    return render(request, "folders/folders.html", {"folders": folders, "form": form})


# --- Mantidos sem alterações de lógica de colaboração (Contas e Home) ---


def home(request):
    if not request.user.is_authenticated:
        return redirect("main:login")
    return render(request, "base/home.html", {"user": request.user})


@login_required()
def welcome(request, id_user):
    if request.user.id != id_user:
        return redirect("main:welcome", id_user=request.user.id)
    # SEGURANÇA: usa request.user diretamente — não rebusca o User pelo id_user da URL,
    # pois o decorator @login_required já garante que request.user é o usuário autenticado.
    user = request.user
    todos = Todo.objects.para_usuario(user).filter(is_active=True)
    return render(request, "base/welcome.html", {"todos": todos, "user": user})


def sobre(request):
    if not request.user.is_authenticated:
        raise Http404()
    return render(request, "base/sobre.html", {"user": request.user})


def create_account(request):
    if request.method == "GET":
        return render(request, "base/new_account.html", {"form": UserForm()})
    elif request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            User.objects.create_user(username=username, password=password)
            return redirect(reverse_lazy("main:login"))
        return render(request, "base/new_account.html", {"form": form})


class CustomLoginView(LoginView):
    template_name = "base/login.html"

    def get_success_url(self):
        return reverse_lazy("main:welcome", kwargs={"id_user": self.request.user.id})

    def form_invalid(self, form):
        messages.error(self.request, "Usuário ou senha inválidos.")
        return super().form_invalid(form)


@login_required
def gerenciar_colaboradores(request, tipo, pk):
    """
    tipo: 'todo' ou 'folder'
    pk: id do objeto
    """
    # 1. Busca o objeto e garante que o usuário logado é o dono
    if tipo == "todo":
        obj = get_object_or_404(Todo, pk=pk, user=request.user)
        titulo = obj.titulo
        back_url = redirect("main:show", id_user=request.user.id, id_anotacao=obj.id)
    else:
        obj = get_object_or_404(Folder, pk=pk, user=request.user)
        titulo = obj.name
        back_url = redirect("main:folders")

    # 2. Lógica para ADICIONAR colaborador
    if request.method == "POST" and "add_user" in request.POST:
        username = request.POST.get("username")
        try:
            user_to_add = User.objects.get(username=username)
            if user_to_add == request.user:
                messages.warning(request, "Você já é o proprietário deste item.")
            else:
                obj.colaboradores.add(user_to_add)
                messages.success(request, f"Usuário {username} adicionado com sucesso!")
        except User.DoesNotExist:
            messages.error(request, "Usuário não encontrado.")
        return redirect(request.path)

    # 3. Lógica para REMOVER colaborador
    if request.method == "POST" and "remove_user" in request.POST:
        user_id = request.POST.get("user_id")
        user_to_remove = get_object_or_404(User, id=user_id)
        obj.colaboradores.remove(user_to_remove)
        messages.success(request, f"Colaborador {user_to_remove.username} removido.")
        return redirect(request.path)

    colaboradores = obj.colaboradores.all()

    context = {
        "obj": obj,
        "titulo": titulo,
        "tipo": tipo,
        "colaboradores": colaboradores,
        "back_url": back_url,
    }
    return render(request, "todo/colaboradores.html", context)


# --- VIEWS PARA GERENCIAR GRUPOS DE COLABORAÇÃO ---


@login_required
def listar_grupos(request):
    """Lista todos os grupos criados pelo usuário"""
    grupos = CollaborationGroup.objects.filter(owner=request.user, is_active=True).prefetch_related(
        "membros"
    )

    context = {
        "grupos": grupos,
    }
    return render(request, "grupos/listar_grupos.html", context)


@login_required
def criar_grupo(request):
    """Cria um novo grupo de colaboração"""
    if request.method == "POST":
        form = CollaborationGroupForm(request.POST, user=request.user)
        if form.is_valid():
            grupo = form.save(commit=False)
            grupo.owner = request.user
            grupo.save()
            form.save_m2m()
            messages.success(request, "Grupo criado com sucesso!")
            return redirect("main:listar_grupos")
    else:
        form = CollaborationGroupForm(user=request.user)

    context = {
        "form": form,
        "titulo": "Criar Novo Grupo",
    }
    return render(request, "grupos/grupo_form.html", context)


@login_required
def editar_grupo(request, grupo_id):
    """Edita um grupo de colaboração"""
    grupo = get_object_or_404(CollaborationGroup, id=grupo_id, owner=request.user, is_active=True)

    if request.method == "POST":
        form = CollaborationGroupForm(request.POST, instance=grupo, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Grupo atualizado com sucesso!")
            return redirect("main:listar_grupos")
    else:
        form = CollaborationGroupForm(instance=grupo, user=request.user)

    context = {
        "form": form,
        "grupo": grupo,
        "titulo": f"Editar Grupo: {grupo.name}",
    }
    return render(request, "grupos/grupo_form.html", context)


@login_required
def deletar_grupo(request, grupo_id):
    """Deleta um grupo de colaboração"""
    grupo = get_object_or_404(CollaborationGroup, id=grupo_id, owner=request.user, is_active=True)

    if request.method == "POST":
        grupo.is_active = False
        grupo.save()
        messages.success(request, f"Grupo '{grupo.name}' removido com sucesso!")
        return redirect("main:listar_grupos")

    context = {
        "grupo": grupo,
    }
    return render(request, "grupos/deletar_grupo.html", context)


@login_required
def gerenciar_membros_grupo(request, grupo_id):
    """Gerencia membros de um grupo (adiciona/remove usuários)"""
    grupo = get_object_or_404(CollaborationGroup, id=grupo_id, owner=request.user, is_active=True)

    # Lógica para ADICIONAR membro
    if request.method == "POST" and "add_user" in request.POST:
        username = request.POST.get("username")
        try:
            user_to_add = User.objects.get(username=username)
            if user_to_add == request.user:
                messages.warning(request, "Você é o proprietário do grupo.")
            elif user_to_add in grupo.membros.all():
                messages.warning(request, f"Usuário {username} já é membro do grupo.")
            else:
                grupo.adicionar_membro(user_to_add)
                messages.success(request, f"Usuário {username} adicionado ao grupo!")
        except User.DoesNotExist:
            messages.error(request, "Usuário não encontrado.")
        return redirect(request.path)

    # Lógica para REMOVER membro
    if request.method == "POST" and "remove_user" in request.POST:
        user_id = request.POST.get("user_id")
        user_to_remove = get_object_or_404(User, id=user_id)
        grupo.remover_membro(user_to_remove)
        messages.success(request, f"Membro {user_to_remove.username} removido do grupo.")
        return redirect(request.path)

    membros = grupo.membros.all()
    form = AddColaboradorForm()

    context = {
        "grupo": grupo,
        "membros": membros,
        "form": form,
    }
    return render(request, "grupos/gerenciar_membros.html", context)


def not_found(request):
    return render(request, "base/404.html")
