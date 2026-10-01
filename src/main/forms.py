from django import forms
from django.db.models import Q
from django.forms import ModelForm, Textarea

from checklist.models import Tarefa
from core.middleware import get_current_user
from main.models import CollaborationGroup, Folder, Image, LinkerTaskTodo, Todo, User


class TodoForm(ModelForm):
    def __init__(self, *args, **kwargs):
        # Removemos o argumento 'user' do kwargs para não dar erro no super()
        user = get_current_user()

        super().__init__(*args, **kwargs)

        # Se o usuário foi passado, filtramos as opções dos campos desejados
        if user:
            self.fields["folder"].queryset = Folder.objects.filter(
                Q(user=user) | Q(colaboradores=user), is_active=True
            ).distinct()

            # Se o campo 'tag' também for associado ao usuário, você pode filtrar da mesma forma:
            # self.fields['tag'].queryset = Tag.objects.filter(user=user)

    class Meta:
        model = Todo
        fields = [
            "titulo",
            "anotacao",
            "prioridade",
            "tag",
            "prazo_inicial",
            "prazo_final",
            "completo",
            "favorito",
            "folder",
        ]

        widgets = {
            # Adicionamos a classe 'textarea' do Bulma aqui
            "anotacao": Textarea(
                attrs={
                    "class": "textarea",
                    "rows": 20,
                    "placeholder": "Escreva sua anotação aqui...",
                }
            ),
            # Adicionamos a classe 'input' do Bulma para os campos de data
            "prazo_final": forms.DateInput(
                attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"
            ),
            "prazo_inicial": forms.DateInput(
                attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"
            ),
        }
        labels = {
            "anotacao": "Anotação",
        }


class TodoFormComColaboradores(ModelForm):
    """Form de Todo com opção de adicionar colaboradores individuais e grupos"""

    class Meta:
        model = Todo
        fields = [
            "titulo",
            "anotacao",
            "prioridade",
            "tag",
            "prazo_inicial",
            "prazo_final",
            "completo",
            "favorito",
            "folder",
            "colaboradores",
            "grupos_colaboracao",
        ]

        widgets = {
            "anotacao": Textarea(
                attrs={
                    "class": "textarea",
                    "rows": 20,
                    "placeholder": "Escreva sua anotação aqui...",
                }
            ),
            "prazo_final": forms.DateInput(
                attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"
            ),
            "prazo_inicial": forms.DateInput(
                attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"
            ),
            "colaboradores": forms.CheckboxSelectMultiple(),
            "grupos_colaboracao": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            # Filtra pastas onde o usuário pode colocar anotações
            self.fields["folder"].queryset = Folder.objects.filter(
                Q(user=user) | Q(colaboradores=user), is_active=True
            ).distinct()

            # Filtra colaboradores - excluindo o próprio usuário
            self.fields["colaboradores"].queryset = User.objects.exclude(id=user.id)

            # Filtra grupos - apenas grupos que o usuário criou
            self.fields["grupos_colaboracao"].queryset = CollaborationGroup.objects.filter(
                owner=user, is_active=True
            )


class UserForm(forms.ModelForm):
    password = forms.CharField(
        label="Senha:",
        widget=forms.PasswordInput(attrs={"class": "input", "placeholder": "Digite sua senha"}),
    )

    class Meta:
        model = User
        fields = ["username", "password"]
        labels = {
            "username": "Nome:",
        }
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "input", "placeholder": "Digite seu nome de usuário"}
            ),
        }


class ImageForm(forms.ModelForm):
    # Configurações de validação de upload
    MAX_UPLOAD_SIZE_MB = 5
    MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

    class Meta:
        model = Image
        # Inclua os campos do seu modelo Image que o usuário deve preencher
        fields = ["titulo", "observacao", "img"]
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "input", "placeholder": "Título da imagem"}),
            "observacao": forms.Textarea(
                attrs={
                    "class": "textarea",
                    "placeholder": "Alguma observação sobre a imagem...",
                    "rows": 3,
                }
            ),
            "img": forms.ClearableFileInput(attrs={"class": "file-input"}),
        }

    def clean_img(self):
        """Valida o arquivo de imagem quanto a extensão, tamanho e conteúdo real (MIME)."""
        import os
        from PIL import Image as PilImage

        image = self.cleaned_data.get("img")
        if not image:
            return image

        # 1. Valida extensão contra allowlist
        _, ext = os.path.splitext(image.name.lower())
        if ext not in self.ALLOWED_EXTENSIONS:
            raise forms.ValidationError(
                f"Extensão '{ext}' não permitida. Use: {', '.join(sorted(self.ALLOWED_EXTENSIONS))}."
            )

        # 2. Valida tamanho máximo
        if image.size > self.MAX_UPLOAD_SIZE_BYTES:
            raise forms.ValidationError(
                f"O arquivo excede o tamanho máximo permitido de {self.MAX_UPLOAD_SIZE_MB} MB."
            )

        # 3. Valida conteúdo real do arquivo via Pillow (não confia apenas na extensão)
        # Pillow re-verifica o stream binário e rejeita arquivos malformados ou não-imagem.
        try:
            pil_image = PilImage.open(image)
            pil_image.verify()  # Detecta arquivos corrompidos ou não-imagem
            # Verifica o formato real reportado pelo Pillow
            pil_format = (pil_image.format or "").lower()
            allowed_pil_formats = {"jpeg", "png", "webp"}
            if pil_format not in allowed_pil_formats:
                raise forms.ValidationError(
                    "O conteúdo do arquivo não corresponde a um formato de imagem permitido."
                )
        except forms.ValidationError:
            raise
        except Exception:
            raise forms.ValidationError(
                "O arquivo enviado não é uma imagem válida ou está corrompido."
            )
        finally:
            # Volta o ponteiro ao início após a validação para uso posterior
            image.seek(0)

        return image


class FolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ["name"]


class FolderFormComColaboradores(forms.ModelForm):
    """Form de Folder com opção de adicionar colaboradores individuais e grupos"""

    class Meta:
        model = Folder
        fields = ["name", "colaboradores", "grupos_colaboracao"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input", "placeholder": "Nome da pasta"}),
            "colaboradores": forms.CheckboxSelectMultiple(),
            "grupos_colaboracao": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            # Filtra colaboradores - excluindo o próprio usuário
            self.fields["colaboradores"].queryset = User.objects.exclude(id=user.id)

            # Filtra grupos - apenas grupos que o usuário criou
            self.fields["grupos_colaboracao"].queryset = CollaborationGroup.objects.filter(
                owner=user, is_active=True
            )


class CollaborationGroupForm(forms.ModelForm):
    """Form para criar e editar grupos de colaboração"""

    class Meta:
        model = CollaborationGroup
        fields = ["name", "descricao", "membros"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input", "placeholder": "Nome do grupo"}),
            "descricao": forms.Textarea(
                attrs={
                    "class": "textarea",
                    "rows": 3,
                    "placeholder": "Descrição do grupo...",
                }
            ),
            "membros": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            # Filtra membros - excluindo o owner do grupo
            self.fields["membros"].queryset = User.objects.exclude(id=user.id)


class AddColaboradorForm(forms.Form):
    """Form simples para adicionar um único colaborador por username"""

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={"class": "input", "placeholder": "Digite o nome do usuário..."}
        ),
        label="Nome de Usuário",
    )


class LinkerTaskTodoForm(forms.ModelForm):
    class Meta:
        model = LinkerTaskTodo
        fields = ["tarefa"]  # O usuário selecionará apenas qual checklist deseja vincular

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            # Filtra o Select para mostrar apenas os checklists ativos do próprio usuário
            self.fields["tarefa"].queryset = Tarefa.objects.filter(user=user, is_active=True)
