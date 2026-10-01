from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render

from .models import Item, Link, Tarefa


@login_required
def checklist(request):
    # Processamento de envio de formulários rápidos
    if request.method == "POST":
        # AÇÃO 1: Criar uma nova Tarefa (apenas com o título)
        if "criar_tarefa" in request.POST:
            titulo = request.POST.get("titulo")
            color = request.POST.get("color", "black")
            if titulo:
                Tarefa.objects.create(titulo=titulo, color=color, user=request.user)
            return redirect("checklist")

        # AÇÃO 2: Adicionar um Item rápido diretamente a uma Tarefa existente
        elif "adicionar_item" in request.POST:
            descricao = request.POST.get("descricao")
            tarefa_id = request.POST.get("tarefa_id")
            if descricao and tarefa_id:
                tarefa_obj = get_object_or_404(Tarefa, id=tarefa_id, user=request.user)
                Item.objects.create(descricao=descricao, tarefa=tarefa_obj, user=request.user)
            return redirect("checklist")

        # AÇÃO 3: Adicionar um Link rápido diretamente a uma Tarefa existente
        elif "adicionar_link" in request.POST:
            url = request.POST.get("url")
            tarefa_id = request.POST.get("tarefa_id")
            if url and tarefa_id:
                tarefa_obj = get_object_or_404(Tarefa, id=tarefa_id, user=request.user)
                Link.objects.create(url=url, tarefa=tarefa_obj, user=request.user)
            return redirect("checklist")
        elif "atualizar_status" in request.POST:
            item_id = request.POST.get("item_id")
            novo_status = request.POST.get("status")
            if item_id and novo_status:
                # Garante que o item pertence ao usuário logado por segurança
                item_obj = get_object_or_404(Item, id=item_id, user=request.user)
                item_obj.feito = novo_status
                item_obj.save()
            return redirect("checklist")

        elif "editar_tarefa" in request.POST:
            tarefa_id = request.POST.get("tarefa_id")
            novo_titulo = request.POST.get("titulo")
            if tarefa_id and novo_titulo:
                tarefa = get_object_or_404(Tarefa, id=tarefa_id, user=request.user)
                tarefa.titulo = novo_titulo
                tarefa.save()
            return redirect("checklist")

        # NOVA AÇÃO 6: Editar a descrição de um Item existente
        elif "editar_item" in request.POST:
            item_id = request.POST.get("item_id")
            nova_descricao = request.POST.get("descricao")
            if item_id and nova_descricao:
                item = get_object_or_404(Item, id=item_id, user=request.user)
                item.descricao = nova_descricao
                item.save()
            return redirect("checklist")

        # NOVA AÇÃO 7: Editar a URL de um Link existente
        elif "editar_link" in request.POST:
            link_id = request.POST.get("link_id")
            nova_url = request.POST.get("url")
            if link_id and nova_url:
                link = get_object_or_404(Link, id=link_id, user=request.user)
                link.url = nova_url
                link.save()
            return redirect("checklist")

        elif "deletar_tarefa" in request.POST:
            tarefa_id = request.POST.get("tarefa_id")
            if tarefa_id:
                tarefa = get_object_or_404(Tarefa, id=tarefa_id, user=request.user)
                tarefa.is_active = False
                tarefa.save()
            return redirect("checklist")

        # NOVA AÇÃO 9: Desativar Item (Soft Delete)
        elif "deletar_item" in request.POST:
            item_id = request.POST.get("item_id")
            if item_id:
                item = get_object_or_404(Item, id=item_id, user=request.user)
                item.is_active = False
                item.save()
            return redirect("checklist")

        # NOVA AÇÃO 10: Desativar Link (Soft Delete)
        elif "deletar_link" in request.POST:
            link_id = request.POST.get("link_id")
            if link_id:
                link = get_object_or_404(Link, id=link_id, user=request.user)
                link.is_active = False
                link.save()
            return redirect("checklist")

    # Carrega os dados do usuário para exibição organizada
    tarefas = Tarefa.objects.filter(user=request.user, is_active=True).prefetch_related(
        Prefetch("itens", queryset=Item.objects.filter(is_active=True)),
        Prefetch("links", queryset=Link.objects.filter(is_active=True)),
    )

    return render(request, "checklist.html", {"tarefas": tarefas})
