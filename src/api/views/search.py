from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agenda.models import AgendaModel
from main.models import AudioRecording, DrawDocument, Folder, Image, Todo


SEARCH_TYPES = {"task", "event", "audio", "drawing", "image", "folder"}
PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


class GlobalSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) > 200:
            raise ValidationError({"q": "A busca deve ter no máximo 200 caracteres."})

        result_type = request.query_params.get("type", "all")
        if result_type != "all" and result_type not in SEARCH_TYPES:
            raise ValidationError({"type": "Tipo de entidade inválido."})

        created_after = self._parse_date(request.query_params.get("created_after"), "created_after")
        created_before = self._parse_date(request.query_params.get("created_before"), "created_before")
        if created_after and created_before and created_after > created_before:
            raise ValidationError({"created_before": "A data final deve ser posterior à data inicial."})

        try:
            page = max(1, int(request.query_params.get("page", "1")))
            page_size = min(
                max(1, int(request.query_params.get("page_size", PAGE_SIZE))),
                MAX_PAGE_SIZE,
            )
        except ValueError as exc:
            raise ValidationError({"page": "Página e tamanho devem ser números inteiros."}) from exc

        user = request.user
        accessible_todos = Todo.objects.para_usuario(user).filter(is_active=True)
        querysets = {
            "task": accessible_todos,
            "event": AgendaModel.objects.filter(user=user, is_active=True),
            "audio": AudioRecording.objects.filter(user=user, is_active=True),
            "drawing": DrawDocument.objects.filter(user=user, is_active=True),
            "image": Image.objects.filter(todo__in=accessible_todos, is_active=True).distinct(),
            "folder": Folder.objects.filter(
                Q(user=user) | Q(colaboradores=user) | Q(grupos_colaboracao__membros=user),
                is_active=True,
            ).distinct(),
        }
        search_fields = {
            "task": ("titulo", "anotacao", "tag"),
            "event": ("titulo", "descricao", "tipo_de_evento"),
            "audio": ("titulo", "audio"),
            "drawing": ("titulo",),
            "image": ("titulo", "descricao", "observacao", "img", "todo__titulo"),
            "folder": ("name",),
        }

        results = []
        total_count = 0
        for entity_type, queryset in querysets.items():
            if result_type not in {"all", entity_type}:
                continue
            if query:
                text_filter = Q()
                for field in search_fields[entity_type]:
                    text_filter |= Q(**{f"{field}__icontains": query})
                queryset = queryset.filter(text_filter)
            if created_after:
                queryset = queryset.filter(created_at__date__gte=created_after)
            if created_before:
                queryset = queryset.filter(created_at__date__lte=created_before)

            total_count += queryset.count()
            results.extend(self._serialize_results(entity_type, queryset))

        results.sort(key=lambda result: (result["created_at"], result["id"]), reverse=True)
        start = (page - 1) * page_size
        page_results = results[start : start + page_size]
        return Response(
            {
                "count": total_count,
                "next": page + 1 if start + page_size < total_count else None,
                "previous": page - 1 if page > 1 else None,
                "results": page_results,
            }
        )

    @staticmethod
    def _parse_date(value, field_name):
        if not value:
            return None
        try:
            parsed = parse_date(value)
        except ValueError:
            parsed = None
        if parsed is None:
            raise ValidationError({field_name: "Informe uma data válida no formato AAAA-MM-DD."})
        return parsed

    @staticmethod
    def _serialize_results(entity_type, queryset):
        if entity_type == "task":
            queryset = queryset.order_by("-created_at", "-id")
            return [
                {
                    "id": item.id,
                    "type": entity_type,
                    "title": item.titulo,
                    "subtitle": item.tag,
                    "created_at": item.created_at,
                    "folder_id": item.folder_id,
                }
                for item in queryset
            ]
        if entity_type == "event":
            queryset = queryset.order_by("-created_at", "-id")
            return [
                {
                    "id": item.id,
                    "type": entity_type,
                    "title": item.titulo,
                    "subtitle": item.tipo_de_evento,
                    "created_at": item.created_at,
                }
                for item in queryset
            ]
        if entity_type == "audio":
            queryset = queryset.select_related("folder").order_by("-created_at", "-id")
            return [
                {
                    "id": item.id,
                    "type": entity_type,
                    "title": item.titulo,
                    "subtitle": item.folder.name if item.folder_id else "Áudio sem pasta",
                    "created_at": item.created_at,
                    "folder_id": item.folder_id,
                }
                for item in queryset
            ]
        if entity_type == "drawing":
            queryset = queryset.select_related("folder").order_by("-created_at", "-id")
            return [
                {
                    "id": item.id,
                    "type": entity_type,
                    "title": item.titulo,
                    "subtitle": item.folder.name if item.folder_id else "Desenho sem pasta",
                    "created_at": item.created_at,
                    "folder_id": item.folder_id,
                }
                for item in queryset
            ]
        if entity_type == "image":
            queryset = queryset.select_related("todo").order_by("-created_at", "-id")
            return [
                {
                    "id": item.id,
                    "type": entity_type,
                    "title": item.titulo,
                    "subtitle": item.todo.titulo,
                    "created_at": item.created_at,
                    "todo_id": item.todo_id,
                }
                for item in queryset
            ]
        queryset = queryset.order_by("-created_at", "-id")
        return [
            {
                "id": item.id,
                "type": entity_type,
                "title": item.name,
                "subtitle": "Pasta",
                "created_at": item.created_at,
            }
            for item in queryset
        ]
