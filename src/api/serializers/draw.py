import re
from math import isfinite

from rest_framework import serializers

from main.models import DrawDocument, Folder, LinkerDrawTodo, Todo


DRAWING_WIDTH = 1000
DRAWING_HEIGHT = 650
MAX_DRAWING_ELEMENTS = 2000
MAX_TEXT_LENGTH = 1000
HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
ELEMENT_FIELDS = {
    "path": {"id", "type", "points", "color", "strokeWidth"},
    "text": {"id", "type", "x", "y", "text", "color", "fontSize"},
    "rect": {"id", "type", "x", "y", "width", "height", "color", "strokeWidth"},
    "roundRect": {"id", "type", "x", "y", "width", "height", "color", "strokeWidth"},
    "circle": {"id", "type", "x", "y", "radius", "color", "strokeWidth"},
    "arrow": {"id", "type", "x1", "y1", "x2", "y2", "color", "strokeWidth"},
}


def _validate_number(value, label, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise serializers.ValidationError(f"{label} deve ser um número.")
    if not isfinite(value) or value < 0 or value > maximum:
        raise serializers.ValidationError(f"{label} fora dos limites permitidos.")


def validate_drawing(value):
    if not isinstance(value, list):
        raise serializers.ValidationError("O desenho deve ser uma lista de elementos.")
    if len(value) > MAX_DRAWING_ELEMENTS:
        raise serializers.ValidationError("O desenho excede o limite de elementos.")

    ids = set()
    for index, element in enumerate(value):
        if not isinstance(element, dict):
            raise serializers.ValidationError(f"Elemento {index + 1} inválido.")
        element_type = element.get("type")
        allowed_fields = ELEMENT_FIELDS.get(element_type)
        if allowed_fields is None or set(element) - allowed_fields:
            raise serializers.ValidationError(f"Elemento {index + 1} possui tipo ou campos inválidos.")
        element_id = element.get("id")
        if not isinstance(element_id, str) or not element_id or len(element_id) > 80 or element_id in ids:
            raise serializers.ValidationError(f"Identificador inválido no elemento {index + 1}.")
        ids.add(element_id)
        color = element.get("color")
        if not isinstance(color, str) or not HEX_COLOR_PATTERN.fullmatch(color):
            raise serializers.ValidationError(f"Cor inválida no elemento {index + 1}.")
        if element_type != "text":
            _validate_number(element.get("strokeWidth"), "Espessura do traço", 30)

        if element_type == "path":
            points = element.get("points")
            if not isinstance(points, list) or not points or len(points) > 10000:
                raise serializers.ValidationError(f"Traço inválido no elemento {index + 1}.")
            for point in points:
                if not isinstance(point, list) or len(point) != 2:
                    raise serializers.ValidationError(f"Ponto inválido no elemento {index + 1}.")
                _validate_number(point[0], "Coordenada X", DRAWING_WIDTH)
                _validate_number(point[1], "Coordenada Y", DRAWING_HEIGHT)
        elif element_type == "text":
            _validate_number(element.get("x"), "Coordenada X", DRAWING_WIDTH)
            _validate_number(element.get("y"), "Coordenada Y", DRAWING_HEIGHT)
            _validate_number(element.get("fontSize"), "Tamanho do texto", 200)
            text = element.get("text")
            if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT_LENGTH:
                raise serializers.ValidationError(f"Texto inválido no elemento {index + 1}.")
        elif element_type == "circle":
            _validate_number(element.get("x"), "Coordenada X", DRAWING_WIDTH)
            _validate_number(element.get("y"), "Coordenada Y", DRAWING_HEIGHT)
            _validate_number(element.get("radius"), "Raio", DRAWING_WIDTH)
        elif element_type == "arrow":
            for key, maximum in (
                ("x1", DRAWING_WIDTH),
                ("x2", DRAWING_WIDTH),
                ("y1", DRAWING_HEIGHT),
                ("y2", DRAWING_HEIGHT),
            ):
                _validate_number(element.get(key), key, maximum)
        else:
            for key, maximum in (
                ("x", DRAWING_WIDTH),
                ("width", DRAWING_WIDTH),
                ("y", DRAWING_HEIGHT),
                ("height", DRAWING_HEIGHT),
            ):
                _validate_number(element.get(key), key, maximum)
    return value


class DrawDocumentSerializer(serializers.ModelSerializer):
    folder = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.filter(is_active=True), allow_null=True, required=False
    )
    folder_name = serializers.CharField(source="folder.name", read_only=True, allow_null=True)

    class Meta:
        model = DrawDocument
        fields = ["id", "titulo", "folder", "folder_name", "drawing", "created_at", "updated_at"]
        read_only_fields = ["id", "folder_name", "created_at", "updated_at"]

    def validate_titulo(self, value):
        titulo = value.strip()
        if not titulo:
            raise serializers.ValidationError("Informe um título para o desenho.")
        return titulo

    def validate_folder(self, value):
        if value is not None and not value.pode_editar(self.context["request"].user):
            raise serializers.ValidationError("Você não tem permissão para usar esta pasta.")
        return value

    def validate_drawing(self, value):
        return validate_drawing(value)


class LinkerDrawTodoSerializer(serializers.ModelSerializer):
    desenho_titulo = serializers.CharField(source="drawing.titulo", read_only=True)
    todo_titulo = serializers.CharField(source="todo.titulo", read_only=True)

    class Meta:
        model = LinkerDrawTodo
        fields = ["id", "todo", "todo_titulo", "drawing", "desenho_titulo", "created_at"]
        read_only_fields = ["id", "todo_titulo", "desenho_titulo", "created_at"]

    def validate(self, attrs):
        request = self.context["request"]
        todo = attrs.get("todo")
        drawing = attrs.get("drawing")
        if todo and not todo.pode_editar(request.user):
            raise serializers.ValidationError(
                {"todo": "Você não pode vincular um desenho a esta tarefa."}
            )
        if drawing and drawing.user_id != request.user.id:
            raise serializers.ValidationError(
                {"drawing": "Você só pode vincular desenhos da sua biblioteca."}
            )
        if todo and drawing and LinkerDrawTodo.objects.filter(
            todo=todo, drawing=drawing, user=request.user, is_active=True
        ).exists():
            raise serializers.ValidationError({"drawing": "Este desenho já está vinculado à tarefa."})
        return attrs
