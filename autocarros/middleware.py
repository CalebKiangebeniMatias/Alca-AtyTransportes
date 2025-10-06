class PermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Adicionar informações de permissão ao contexto
        if hasattr(request, 'user') and request.user.is_authenticated:
            request.user._perm_cache = {
                'is_admin': request.user.is_admin(),
                'is_gestor': request.user.is_gestor(),
                'can_edit': request.user.can_edit(),
                'can_view_only': request.user.can_view_only(),
            }
