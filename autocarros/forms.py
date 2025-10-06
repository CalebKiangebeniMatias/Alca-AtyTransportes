from django import forms
from .models import (
    Comprovativo, ComprovativoRelatorio, DespesaCombustivel,
    EstadoAutocarro, RegistoDiario, Autocarro, Despesa,
    RelatorioSector, Sector
)
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from .models import CustomUser



User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    telefone = forms.CharField(max_length=15, required=False)
    nivel_acesso = forms.ChoiceField(choices=CustomUser.NIVEL_ACESSO_CHOICES)
    
    class Meta:
        model = User
        fields = ('username', 'email',)
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='Username ou Email',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']

# ==================== FORMULÁRIOS ==================== #

class SectorForm(forms.ModelForm):
    class Meta:
        model = Sector
        fields = ["nome"]
        widgets = {
            "nome": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Digite o nome do setor"
            }),
        }


class SectorGestorForm(forms.ModelForm):
    gestor = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(nivel_acesso='GESTOR'),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Sector
        fields = ['nome', 'slug', 'gestor']



# ---- Widget para múltiplos arquivos ---- #
class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


# ---- Relatório por Setor ---- #
class RelatorioSectorForm(forms.ModelForm):
    class Meta:
        model = RelatorioSector
        fields = ['sector', 'data', 'descricao']
        widgets = {
            'sector': forms.Select(attrs={'class': 'form-select'}),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'comprovativo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descreva observações do relatório'
            }),
        }


# ---- Registo Diário ---- #
class RegistoDiarioForm(forms.ModelForm):
    class Meta:
        model = RegistoDiario
        exclude = ['autocarro']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'normal': forms.NumberInput(attrs={'class': 'form-control'}),
            'alunos': forms.NumberInput(attrs={'class': 'form-control'}),
            'luvu': forms.NumberInput(attrs={'class': 'form-control'}),
            'frete': forms.NumberInput(attrs={'class': 'form-control'}),
            'alimentacao': forms.NumberInput(attrs={'class': 'form-control'}),
            'parqueamento': forms.NumberInput(attrs={'class': 'form-control'}),
            'taxa': forms.NumberInput(attrs={'class': 'form-control'}),
            'outros': forms.NumberInput(attrs={'class': 'form-control'}),
            'numero_passageiros': forms.NumberInput(attrs={'class': 'form-control'}),
            'numero_viagens': forms.NumberInput(attrs={'class': 'form-control'}),
            'km_percorridos': forms.NumberInput(attrs={'class': 'form-control'}),
            'motorista': forms.TextInput(attrs={'class': 'form-control'}),
            'cobrador_principal': forms.TextInput(attrs={'class': 'form-control'}),
            'cobrador_auxiliar': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Nenhum campo obrigatório
        for field in self.fields.values():
            field.required = False

    def clean(self):
        cleaned_data = super().clean()
        # valores padrão para números
        for field_name, field in self.fields.items():
            if isinstance(field, (forms.DecimalField, forms.IntegerField)):
                if not cleaned_data.get(field_name):
                    cleaned_data[field_name] = 0
        # valores padrão para textos
        for text_field in ["motorista", "cobrador_principal", "cobrador_auxiliar"]:
            if not cleaned_data.get(text_field):
                cleaned_data[text_field] = "N/A"
        return cleaned_data


# ---- Autocarro ---- #
class AutocarroForm(forms.ModelForm):
    class Meta:
        model = Autocarro
        fields = ['numero', 'modelo', 'placa', 'sector']
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: AC001'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Mercedes-Benz OF-1721'}),
            'placa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: LD-12-34-AB'}),
            'sector': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_numero(self):
        return self.cleaned_data['numero'].upper()

    def clean_placa(self):
        return self.cleaned_data['placa'].upper()


# ---- Estado do Autocarro ---- #
class EstadoAutocarroForm(forms.ModelForm):
    class Meta:
        model = EstadoAutocarro
        fields = [
            "autocarro", "motor_funciona", "pneus_bons", "luzes_funcionam",
            "travoes_bons", "parabrisas_ok", "bancos_bons", "observacoes"
        ]
        widgets = {
            "autocarro": forms.Select(attrs={"class": "form-select"}),
            "motor_funciona": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "pneus_bons": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "luzes_funcionam": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "travoes_bons": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "parabrisas_ok": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "bancos_bons": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


# ---- Despesa ---- #
class DespesaForm(forms.ModelForm):
    class Meta:
        model = Despesa
        fields = ["descricao", "valor", "data", "numero_transacao", "numero_requisicao", "sector"]
        widgets = {
            "valor": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Digite o valor da despesa"}),
            "data": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "descricao": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Descreva a despesa"
            }),
            "numero_transacao": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nº da transação"}),
            "numero_requisicao": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nº da requisição"}),
            "sector": forms.Select(attrs={"class": "form-control"}),
        }


# ---- Formset para múltiplos comprovativos ---- #
ComprovativoFormSet = forms.modelformset_factory(
    Comprovativo,
    fields=("arquivo",),
    extra=3,
    can_delete=True,
    widgets={"arquivo": forms.ClearableFileInput(attrs={"class": "form-control"})}
)


# ---- Formset para múltiplos Registos Diários ---- #
RegistoDiarioFormSet = forms.modelformset_factory(
    RegistoDiario,
    form=RegistoDiarioForm,
    extra=0,          # não adiciona formulários extras
    can_delete=True   # permite apagar registros
)


# ---- Selecionar setor para combustível ---- #
class SelecionarSectorCombustivelForm(forms.Form):
    sector = forms.ModelChoiceField(
        queryset=Sector.objects.all(),
        label="Escolha um setor",
        widget=forms.Select(attrs={"class": "form-select"})
    )


# ---- Despesa de Combustível ---- #
class DespesaCombustivelForm(forms.ModelForm):
    class Meta:
        model = DespesaCombustivel
        fields = [
            "valor", "valor_litros", "comprovativo", "sector",
            "autocarro", "data", "descricao", "sobragem_filtros", "lavagem"
        ]
        widgets = {
            "valor": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "valor_litros": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "comprovativo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "data": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "descricao": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "sobragem_filtros": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "lavagem": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    # sobrescreve para aceitar vazio
    data = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )
    sector = forms.ModelChoiceField(queryset=Sector.objects.all(), widget=forms.HiddenInput())
    autocarro = forms.ModelChoiceField(queryset=Autocarro.objects.all(), widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sector"].queryset = Sector.objects.all()
        self.fields["autocarro"].queryset = Autocarro.objects.all()


# ---- Comprovativos do Relatório ---- #


from django import forms

# 🔹 WIDGET PERSONALIZADO PARA MÚLTIPLOS ARQUIVOS
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

# 🔹 FORMULÁRIO SIMPLES PARA MÚLTIPLOS ARQUIVOS
class MultiFileForm(forms.Form):
    arquivos = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'multiple': True,
            'accept': 'image/*,.pdf,.doc,.docx'
        })
    )


def get_comprovativo_formset():
    """Retorna um formset para comprovativos de relatório"""
    return forms.modelformset_factory(
        ComprovativoRelatorio,
        fields=('arquivo', 'descricao'),
        extra=3,
        can_delete=True,
        widgets={
            'arquivo': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'multiple': True,
                'accept': 'image/*,.pdf,.doc,.docx'
            }),
            'descricao': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrição do comprovativo'
            }),
        }
    )

