from django.forms import ModelForm
from .models import Colors, AgendaModel
from django import forms


class ColorForm(ModelForm):
    class Meta:
        model = Colors
        fields = ["cor_de_destaque"]


class AgendaForm(ModelForm):
    class Meta:
        model = AgendaModel
        fields = [
            "titulo",
            "tipo_de_evento",
            "descricao",
            "dia_do_evento",
            "importancia",
        ]
        widgets = {
            "dia_do_evento": forms.DateInput(
                attrs={
                    "type": "date",  # Isso usará o widget de data nativo do navegador
                    "class": "form-control",  # Exemplo de classe CSS (Bootstrap)
                },
                format="%Y-%m-%d",  # Formato que o widget espera/envia (ISO 8601 é bom para type='date')
            ),
        }
