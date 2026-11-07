import mimetypes

from django.http import FileResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.permissions.image import IsImageOwner
from api.serializers.image import ImageSerializer
from main.models import Image, Todo


class ImageViewSet(viewsets.ModelViewSet):
    serializer_class = ImageSerializer
    permission_classes = [IsAuthenticated, IsImageOwner]

    def get_queryset(self):
        qs = Image.objects.filter(
            todo__in=Todo.objects.para_usuario(self.request.user),
            todo__is_active=True,
        ).distinct()
        todo_id = self.request.query_params.get("todo")
        if todo_id:
            qs = qs.filter(todo_id=todo_id)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=["get"], url_path="file")
    def file(self, request, pk=None):
        image = self.get_object()
        if not image.img:
            raise NotFound("Arquivo de imagem não encontrado.")
        try:
            image_file = image.img.open("rb")
        except FileNotFoundError as exc:
            raise NotFound("Arquivo de imagem não encontrado.") from exc

        content_type = mimetypes.guess_type(image.img.name)[0] or "application/octet-stream"
        response = FileResponse(image_file, content_type=content_type)
        response["X-Content-Type-Options"] = "nosniff"
        return response
