from django import template

# Cria uma instância da biblioteca de templates para registrar nossos filtros
register = template.Library()


@register.filter(name="get_item")
def get_item(dictionary, key):
    """
    Permite acessar um item de um dicionário usando uma variável como chave no template.
    Uso: {{ meu_dicionario|get_item:minha_chave }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
