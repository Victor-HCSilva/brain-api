import uuid

from django.contrib.auth.models import User
from django.db import IntegrityError, models
from django.db.models import Q
from django.utils import timezone
from core.models.mixins import ActivableAndTimeStamp

# Assumindo que estes imports existem no seu projeto
# from checklist.models import Tarefa
# from main.utils import get_time_remainder

# --- MANAGER PARA LÓGICA DE COLABORAÇÃO ---


MAX_LENGTH = 100
TEXT_AREA_LIMIT = 15000


class TodoQuerySet(models.QuerySet):
    def para_usuario(self, user):
        """
        Retorna apenas os Todos que o usuário tem permissão para ver:
        1. É o dono do Todo.
        2. É um colaborador direto do Todo.
        3. É um colaborador da Pasta onde o Todo está.
        4. É o dono da Pasta onde o Todo está.
        5. Pertence a um grupo que tem acesso ao Todo.
        6. Pertence a um grupo que tem acesso à Pasta.
        """
        if user.is_anonymous:
            return self.none()

        # Busca os grupos aos quais o usuário pertence
        user_groups = CollaborationGroup.objects.filter(membros=user)

        return self.filter(
            Q(user=user)
            | Q(colaboradores=user)
            | Q(grupos_colaboracao__in=user_groups)
            | Q(folder__colaboradores=user)
            | Q(folder__grupos_colaboracao__in=user_groups)
            | Q(folder__user=user)
        ).distinct()


class TodoManager(models.Manager):
    def get_queryset(self):
        return TodoQuerySet(self.model, using=self._db)

    def para_usuario(self, user):
        return self.get_queryset().para_usuario(user)


# --- MODELO DE COLABORAÇÃO: GRUPOS ---


class CollaborationGroup(ActivableAndTimeStamp):
    """
    Modelo para gerenciar grupos de colaboradores.
    Um grupo pode conter múltiplos usuários e compartilhar acesso a Todos e Pastas.
    """

    name = models.CharField(max_length=MAX_LENGTH)
    descricao = models.TextField(default="", blank=True, max_length=MAX_LENGTH)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="grupos_que_criei")
    membros = models.ManyToManyField(User, related_name="grupos_que_participo", blank=True)

    class Meta:
        unique_together = ["name", "owner"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} (criado por {self.owner.username})"

    def adicionar_membro(self, user):
        """Adiciona um usuário ao grupo"""
        if user not in self.membros.all():
            self.membros.add(user)
            return True
        return False

    def remover_membro(self, user):
        """Remove um usuário do grupo"""
        if user in self.membros.all():
            self.membros.remove(user)
            return True
        return False

    def pode_gerenciar(self, user):
        """Verifica se o usuário pode gerenciar este grupo"""
        return user == self.owner


# --- MODELOS ---


class Folder(ActivableAndTimeStamp):
    name = models.CharField(default="folder", max_length=MAX_LENGTH)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="minhas_pastas")
    colaboradores = models.ManyToManyField(User, related_name="pastas_compartilhadas", blank=True)
    grupos_colaboracao = models.ManyToManyField(
        CollaborationGroup, related_name="pastas_compartilhadas", blank=True
    )

    def __str__(self):
        return f"{self.name}"

    def save(self, *args, **kwargs):
        try:
            super().save(*args, **kwargs)
        except IntegrityError:
            suffix = str(uuid.uuid4())[:8]
            self.name = f"{self.name[:90]}+{suffix}"
            super().save(*args, **kwargs)

    class Meta:
        unique_together = ["name", "user"]

    def pode_editar(self, user):
        """Verifica se o usuário pode editar a pasta"""
        if user == self.user:
            return True
        if self.colaboradores.filter(id=user.id).exists():
            return True
        if self.grupos_colaboracao.filter(membros=user).exists():
            return True
        return False

    def pode_excluir(self, user):
        """Apenas o dono pode excluir"""
        return user == self.user


class Todo(ActivableAndTimeStamp):
    TAGS = [
        ("Atividade", "Atividade"),
        ("Anotação", "Anotação"),
        ("Prova", "prova"),
        ("Arquivo", "Arquivo"),
        ("Urgente", "Urgente"),
        ("Importante.", "Importante"),
        ("Tarefa", "Tarefa"),
        ("Link", "Link"),
        ("Lembrete.", "Lembrete"),
        ("Avulso", "Avulso"),
        ("Outro", "Outro"),
    ]
    PRIORIDADES = [
        ("Baixa", "Baixa"),
        ("Média", "Média"),
        ("Alta", "Alta"),
        ("1", "Baixa (Legado)"),
        ("2", "Média (Legado)"),
        ("3", "Alta (Legado)"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="meus_todos")
    titulo = models.CharField(max_length=MAX_LENGTH, default="Sem titulo")
    favorito = models.BooleanField(default=False)
    completo = models.BooleanField(default=False)
    anotacao = models.TextField(
        ("Anotação"), default="Escreva algo aqui!", max_length=TEXT_AREA_LIMIT
    )
    prioridade = models.CharField(choices=PRIORIDADES, max_length=MAX_LENGTH, default="Baixa")
    tag = models.CharField(choices=TAGS, max_length=MAX_LENGTH, default="Avulso")
    prazo_inicial = models.DateTimeField(
        default=timezone.now, help_text=f"{str(timezone.now().date())}"
    )
    prazo_final = models.DateTimeField(
        default=timezone.now, help_text=f"{str(timezone.now().date())}"
    )
    email_notification_at = models.DateTimeField(null=True, blank=True)
    email_notification_message = models.CharField(max_length=500, blank=True, default="")
    email_notification_sent_at = models.DateTimeField(null=True, blank=True, editable=False)
    is_active = models.BooleanField(default=True)

    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, blank=True, null=True, related_name="todos"
    )
    colaboradores = models.ManyToManyField(User, related_name="todos_compartilhados", blank=True)
    grupos_colaboracao = models.ManyToManyField(
        CollaborationGroup, related_name="todos_compartilhados", blank=True
    )

    # Ativa o manager customizado
    objects = TodoManager()

    def __str__(self):
        return self.titulo

    # --- Lógica de Permissão ---
    def pode_editar(self, user):
        """Verifica se o usuário pode alterar o conteúdo"""
        if user == self.user:
            return True
        if self.colaboradores.filter(id=user.id).exists():
            return True
        if self.grupos_colaboracao.filter(membros=user).exists():
            return True
        if self.folder and self.folder.pode_editar(user):
            return True
        return False

    def pode_excluir(self, user):
        """Geralmente apenas o dono ou o dono da pasta pode excluir"""
        return user == self.user or (self.folder and user == self.folder.user)

    # --- Propriedades de Interface ---
    @property
    def prazo_dias(self):
        if self.prazo_final:
            # Importado no topo se necessário: from main.utils import get_time_remainder
            try:
                from main.utils import get_time_remainder

                return get_time_remainder(self.prazo_final)
            except ImportError:
                delta = self.prazo_final - timezone.now().date()
                return delta.days
        return None

    def message(self):
        dias = self.prazo_dias
        if dias is None:
            return ""
        return "Passou do prazo: " if dias <= 0 else "Dias restantes: "

    @property
    def color(self):
        dias = self.prazo_dias
        match dias:
            case None:
                return "gray"
            case x if x >= 7:
                return "#00ff00"
            case x if 3 <= x < 7:
                return "orange"
            case x if 1 <= x <= 2:
                return "violet"
            case _:
                return "#b82b14"


def _upload_imagem_path(instance, filename):
    """Gera um caminho de upload com nome UUID para a imagem.
    SEGURANÇA: Nunca usa o nome original do arquivo enviado pelo usuário,
    prevenindo path traversal e vazamento de informações via nomes de arquivo.
    """
    import uuid
    import os

    ext = os.path.splitext(filename)[1].lower()
    return f"imgs/{uuid.uuid4().hex}{ext}"


class Image(ActivableAndTimeStamp):
    img = models.ImageField(upload_to=_upload_imagem_path)
    descricao = models.CharField(max_length=MAX_LENGTH, default="Imagem sem descriçao")
    titulo = models.CharField(max_length=MAX_LENGTH, default="Sem titulo")
    data_de_criacao = models.DateTimeField(default=timezone.now)
    # Alterado para apontar para o Todo (Pai)
    todo = models.ForeignKey(Todo, on_delete=models.CASCADE, related_name="imagens")
    observacao = models.CharField(default="Sem observação", max_length=100)

    def __str__(self):
        return f"Imagem: {self.titulo} - Ref Todo: {self.todo.titulo}"


class LinkerTaskTodo(ActivableAndTimeStamp):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    todo = models.ForeignKey(Todo, on_delete=models.CASCADE, related_name="vinculos_tarefas")
    # Supondo que Tarefa venha de checklist.models
    tarefa = models.ForeignKey(
        "checklist.Tarefa", on_delete=models.CASCADE, related_name="vinculos_anotacoes"
    )

    def __str__(self):
        return f"{self.user.username} | {self.todo.titulo}"

    class Meta:
        unique_together = ["todo", "user", "tarefa"]


def _upload_audio_path(instance, filename):
    import os

    ext = os.path.splitext(filename)[1].lower()
    return f"audios/{uuid.uuid4().hex}{ext}"


class AudioRecording(ActivableAndTimeStamp):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="audio_gravacoes")
    titulo = models.CharField(max_length=MAX_LENGTH)
    audio = models.FileField(upload_to=_upload_audio_path)
    folder = models.ForeignKey(
        Folder, on_delete=models.SET_NULL, blank=True, null=True, related_name="audio_gravacoes"
    )

    def __str__(self):
        return self.titulo


class LinkerAudioTodo(ActivableAndTimeStamp):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    todo = models.ForeignKey(Todo, on_delete=models.CASCADE, related_name="vinculos_audios")
    audio = models.ForeignKey(
        AudioRecording, on_delete=models.CASCADE, related_name="vinculos_todo"
    )

    class Meta:
        unique_together = ["todo", "user", "audio"]


class DrawDocument(ActivableAndTimeStamp):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="desenhos")
    titulo = models.CharField(max_length=MAX_LENGTH)
    folder = models.ForeignKey(
        Folder, on_delete=models.SET_NULL, blank=True, null=True, related_name="desenhos"
    )
    drawing = models.JSONField(default=list)

    def __str__(self):
        return self.titulo


class LinkerDrawTodo(ActivableAndTimeStamp):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    todo = models.ForeignKey(Todo, on_delete=models.CASCADE, related_name="vinculos_desenhos")
    drawing = models.ForeignKey(
        DrawDocument, on_delete=models.CASCADE, related_name="vinculos_todo"
    )

    class Meta:
        unique_together = ["todo", "user", "drawing"]
