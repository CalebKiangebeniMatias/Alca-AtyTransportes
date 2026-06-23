from django.apps import AppConfig



# <----- Configuração da app "autocarros" -----> #
class AutocarrosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'autocarros'

class ContabilidadeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'contabilidade'
    verbose_name = 'Contabilidade'
