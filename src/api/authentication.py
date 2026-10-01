import re
from typing import Optional
from rest_framework_simplejwt.authentication import JWTAuthentication


class FlexibleJWTAuthentication(JWTAuthentication):
    """
    Autenticação JWT flexível e resiliente.

    Aceita de forma transparente:
    - 'Bearer <token>' (padrão)
    - 'Bearer Bearer <token>' (duplicação acidental em clientes/proxies)
    - '<token>' direto (sem prefixo Bearer, comum em testes/Swagger/Postman)

    Se o cabeçalho estiver vazio, contiver apenas 'Bearer' (com ou sem espaços)
    ou prefixos incompletos, retorna None de forma segura em vez de disparar
    a exceção 'bad_authorization_header' ("Cabeçalho de autorização deve conter dois valores delimitados por espaço").
    """

    def get_raw_token(self, header: bytes) -> Optional[bytes]:
        if not header:
            return None

        try:
            header_str = header.decode("latin1").strip()
        except UnicodeDecodeError:
            header_str = header.decode("utf-8", errors="ignore").strip()

        if not header_str:
            return None

        # Remove qualquer prefixo 'bearer' repetido (com ou sem espaços)
        token_str = re.sub(r"^(bearer\s*)+", "", header_str, flags=re.IGNORECASE).strip()

        if not token_str or token_str.lower() in ("bearer", "jwt"):
            return None

        # Se houver múltiplos blocos delimitados por espaço, pega o primeiro bloco que não seja bearer
        parts = token_str.split()
        if not parts:
            return None

        clean_token = parts[0]
        if clean_token.lower() in ("bearer", "jwt"):
            return None

        return clean_token.encode("latin1")
