import io
import logging
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseServerError
from text_to_audio.engine import TextToAudio
from text_to_audio.dto import AnotationDTO
from main.models import Todo, User

logger = logging.getLogger(__name__)

def read_todo(request, user_id: int, todo_id: int):
    # Se você usar autenticação padrão do Django, prefira request.user em vez de user_id na URL
    user = get_object_or_404(User, id=user_id)
    todo = get_object_or_404(Todo, id=todo_id)

    # 1. Validação de permissão
    if todo.user != user:
        return HttpResponseForbidden("Você não tem permissão para acessar esta anotação.")

    try:
        # 2. Gera o áudio em memória
        engine = TextToAudio(
            AnotationDTO(
                title=todo.title,
                content=todo.anotacao,
                created_at=todo.created_at,
                prazo_final=todo.prazo_final
            )
        )
        audio_bytes = engine.convert()  # Deve retornar bytes do áudio (ex: b'...mp3...')

        if not audio_bytes:
            return HttpResponseServerError("Não foi possível gerar o áudio.")

        # 3. Retorna os bytes diretamente na resposta HTTP
        response = HttpResponse(audio_bytes, content_type="audio/mpeg")  # ou "audio/wav"
        
        # 'inline' instrui o navegador a tocar o áudio diretamente no player nativo
        response['Content-Disposition'] = f'inline; filename="todo_{todo.id}.mp3"'
        
        return response

    except Exception as e:
        logger.error(f"Erro ao gerar áudio do todo {todo_id}: {e}", exc_info=True)
        return HttpResponseServerError("Erro interno ao processar áudio.")