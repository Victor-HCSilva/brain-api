from dataclasses import dataclass
from datetime import datetime

@dataclass
class AnotationDTO:
    title: str
    content: str
    created_at: datetime
    prazo_final: datetime

    def _initial(self):
        prefix = f"Você vai ouvir a anotação {self.title}. Criada em"
        if self.prazo_final < datetime.now() :
            return f"{prefix} {self.created_at.date()} que passou do prazo."
        return f"{prefix} {self.created_at.date()} com data prevista de conclusão \
em {self.prazo_final.date()}."

    def formated_text(self):
        return self._initial() + self.content