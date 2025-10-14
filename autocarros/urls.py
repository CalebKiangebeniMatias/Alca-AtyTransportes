# urls.py
from django.shortcuts import redirect
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.contrib.auth import views as auth_views


# Define os padrões de URL para a app "autocarros"
urlpatterns = [

    # Autenticação
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    # urls.py
    path('register/', views.register_user, name='register'),


    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('perfil/', views.perfil, name='perfil'),


    path('admin/usuarios/', views.gerir_usuarios, name='gerir_usuarios'),
    path('admin/usuarios/editar/<int:user_id>/', views.editar_usuario, name='editar_usuario'),
    
    path('associar-gestor/<int:sector_id>/', views.associar_gestor, name='associar_gestor'),

    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset.html'),name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    
    # Acesso Negado
    path('acesso-negado/', views.acesso_negado, name='acesso_negado'),

    # ... outras URLs
    path('verificar-integridade/', views.verificar_integridade, name='verificar_integridade'),

    # Setores
    path("sectores/", views.lista_sectores, name="lista_sectores"),
    path("sectores/adicionar/", views.adicionar_sector, name="adicionar_sector"),
    path("sectores/<int:pk>/editar/", views.editar_sector, name="editar_sector"),
    path("sectores/<int:pk>/apagar/", views.apagar_sector, name="apagar_sector"),

    # Painel de Controle
    path('', views.dashboard, name='dashboard'),
    path('autocarro/<int:autocarro_id>/', views.detalhe_autocarro, name='detalhe_autocarro'),

    # Relatórios Diários por Sector
    path("registros/", views.listar_registros, name="listar_registros"),
    path("relatorios/adicionar/", views.adicionar_relatorio_sector, name="adicionar_relatorio_sector"),
    path('registros/editar/<int:pk>/', views.editar_relatorio_sector, name='editar_relatorio_sector'),
    path('registos/<int:pk>/deletar/', views.deletar_relatorio_sector, name='deletar_relatorio_sector'),

    # Detalhes do Relatório Diário por Sector
    path('relatorios/<int:pk>/adicionar-comprovativos/', views.adicionar_comprovativos, name='adicionar_comprovativos'),
    path('comprovativos/<int:pk>/deletar/', views.deletar_comprovativo, name='deletar_comprovativo'),
    path('relatorios/<int:pk>/concluir/', views.concluir_relatorio, name='concluir_relatorio'),
    path('relatorios/<int:pk>/validar/', views.validar_relatorio, name='validar_relatorio'),
    path('relatorios-validados/', views.relatorios_validados, name='relatorios_validados'),
    path('registros/<int:pk>/deletar/', views.deletar_registro, name='deletar_registro'),
    path('registros/deletar-grupo/<int:sector_id>/<str:data>/', views.deletar_registros_sector_data, name='deletar_registros_sector_data'),

    # Autocarros
    path('autocarros/', views.listar_autocarros, name='listar_autocarros'),
    path('autocarros/cadastrar/', views.cadastrar_autocarro, name='cadastrar_autocarro'),
    path('autocarros/editar/<int:pk>/', views.editar_autocarro, name='editar_autocarro'),
    path('autocarros/deletar/<int:pk>/', views.deletar_autocarro, name='deletar_autocarro'),
    path("autocarros/atualizar-estado/", views.atualizar_estado, name="atualizar_estado"),
    path("autocarros/<int:pk>/status/", views.alterar_status_autocarro, name="alterar_status_autocarro"),


    # Despesas normais ou variavéis
    path('despesas/adicionar/', views.adicionar_despesa, name='adicionar_despesa'),
    path('despesas/', views.listar_despesas, name='listar_despesas'),
    path('despesas/<int:pk>/editar/', views.editar_despesa, name='editar_despesa'),
    path('despesas/<int:pk>/deletar/', views.deletar_despesa, name='deletar_despesa'),
    
    # Despesas Combústivel
    path("despesas/selecionar-sector/", views.selecionar_sector_combustivel, name="selc_sector_cumb"),
    path('despesas/combustivel/', views.listar_combustivel, name='listar_combustivel'),
    path("despesas/adicionar/<int:pk>/", views.adicionar_combustivel, name="adicionar_combustivel"),
    path("despesas/combustivel/<int:pk>/editar/", views.editar_combustivel, name="editar_combustivel"),
    path("despesas/combustivel/<int:pk>/deletar/", views.deletar_combustivel, name="deletar_combustivel"),

    # Setor
    path("regiao/<slug:slug>/", views.resumo_sector, name="resumo_sector"),

    # Gerencia
    path("contabilista-financas/", views.contabilista_financas, name="contabilista_financas"),
    path("gerencia-financas/", views.gerencia_financas, name="gerencia_financas"),
    path("gerencia-campo/", views.gerencia_campo, name="gerencia_campo"),

    path('', lambda request: redirect('login')),

    #exportar relatório mensal
    path("exportar-relatorio-dashboard/", views.exportar_relatorio_dashboard, name="exportar_relatorio_dashboard"),

]



# Servir arquivos de mídia em modo DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
