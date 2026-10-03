from datetime import datetime

from gtts import gTTS

path = f"audio-{datetime.now()}.mp3"
eng = {
    "text": "Welcome to Hello World, you best web app",
    "lang": "eng",
    "tld": "com.au",
}
pt = {
    "text": "Olá, este é um pequeno teste de conversão de áudio para texto. Estou falando de forma natural, com algumas pausas e diferentes palavras para verificar a precisão da transcrição. O objetivo é descobrir se a biblioteca consegue reconhecer corretamente minha voz, a pontuação e a estrutura das frases.",
    "lang": "pt-br",
    "tld": "com.br",
}

if __name__ == "__main__":
    tts = gTTS(**pt)
    tts.save(path)
