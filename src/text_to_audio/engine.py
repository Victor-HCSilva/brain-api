from datetime import datetime
from io import BytesIO

from gtts import gTTS

from text_to_audio.dto import AnotationDTO
from text_to_audio.clean import markdown_com_contexto


class TextToAudio:
    def __init__(self, a: AnotationDTO):
        self.anotation = a
        self.config = {
            "text": "",
            "lang": "pt-br",
            "tld": "com.br",
        }

    def convert(self) -> bytes:
        self.config["text"] = markdown_com_contexto(self.anotation.formated_text())

        g = gTTS(**self.config)
        g.save("out.mp3")
        audio = BytesIO()
        g.write_to_fp(audio)
        return audio.getvalue()


if __name__ == "__main__":
    content = f"""
     # Relatório Mensal
    Este é um texto com uma *palavra importante* e outra em **negrito**.

    - Primeiro item
    - Segundo item com [link](https://exemplo.com)
    """

    t = TextToAudio(
        AnotationDTO(
           title="O teste",
           content=content,
           created_at = datetime(2020, 2, 1),
           # prazo_final = datetime(2020, 3, 1) # passou do prazo
           prazo_final = datetime(2090, 3, 1)   # Não passou do prazo
        )
    )
    t.convert()
