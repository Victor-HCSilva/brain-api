import re

def markdown_com_contexto(md_text: str) -> str:
    # 1. Títulos (# Titulo -> Título: ...)
    # Trata de # até ######
    md_text = re.sub(r'^(#{1,6})\s*(.+)$', r'Título: \2', md_text, flags=re.MULTILINE)

    # 2. Itens de lista / tópicos (- item ou * item no início da linha)
    md_text = re.sub(r'^\s*[-*+]\s+(.+)$', r'Tópico: \1', md_text, flags=re.MULTILINE)

    # 3. Negrito (**texto** ou __texto__) -> [Destaque: texto]
    md_text = re.sub(r'(\*\*|__)(.*?)\1', r'destaque: \2', md_text)

    # 4. Itálico (*texto* ou _texto_)
    md_text = re.sub(r'(\*|_)(.*?)\1', r'\2', md_text)

    # 5. Links [texto](url) -> texto (url)
    md_text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (link: \2)', md_text)

    # 6. Blocos de código `código` -> código
    md_text = re.sub(r'`([^`]+)`', r'\1', md_text)

    return md_text


if __name__ == "__main__":
    texto_md = """
    # Relatório Mensal
    Este é um texto com uma *palavra importante* e outra em **negrito**.

    - Primeiro item
    - Segundo item com [link](https://exemplo.com)
    """
    print(markdown_com_contexto(texto_md))