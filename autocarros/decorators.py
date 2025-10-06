from django.shortcuts import redirect
from functools import wraps

def acesso_restrito(niveis_permitidos):
    """
    Decorador para restringir acesso com base no nível do usuário.
    Exemplo de uso: @acesso_restrito(['ADMIN', 'GESTOR'])
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Verifica se o usuário está autenticado
            if not request.user.is_authenticated:
                return redirect('login')

            # Verifica se o usuário tem o nível permitido
            if hasattr(request.user, 'nivel_acesso'):
                if request.user.nivel_acesso not in niveis_permitidos and not request.user.is_superuser:
                    return redirect('acesso_negado')
            else:
                # Caso o user não tenha o campo nivel_acesso (usuário padrão Django)
                return redirect('acesso_negado')

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
