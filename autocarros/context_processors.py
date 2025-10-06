from .models import Sector

def sectores_context(request):
    return {
        "sectores": Sector.objects.all()
    }
