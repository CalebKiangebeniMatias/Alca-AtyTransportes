from django.shortcuts import redirect
from functools import wraps
from django.contrib import messages

def acesso_restrito(niveis_permitidos):
    """
    Decorador para restringir acesso com base no nível do usuário.
    Exemplo de uso: @acesso_restrito(['admin', 'gestor'])
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # 🔹 Verifica se o usuário está autenticado
            if not request.user.is_authenticated:
                messages.warning(request, "Você precisa fazer login para acessar esta página.")
                return redirect('login')

            # 🔹 Verifica o nível de acesso
            nivel = getattr(request.user, 'nivel_acesso', None)
            if nivel not in niveis_permitidos and not request.user.is_superuser:
                messages.error(request, "Acesso negado. Você não tem permissão para acessar esta página.")
                return redirect('acesso_negado')  # ou qualquer outra view de erro

            # 🔹 Permite o acesso
            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator
