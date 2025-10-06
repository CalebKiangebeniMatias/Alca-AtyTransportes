from pathlib import Path, os


BASE_DIR = Path(__file__).resolve().parent.parent

# Diretório onde os uploads serão armazenados
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

SECRET_KEY = 'django-insecure-kj3o(9&x@6)5uc#02ok*_ck9wlvg%&z0=d*@!8n19q$xkn$439'
DEBUG = True
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "0.0.0.0",
    "192.168.7.33",
]

AUTH_USER_MODEL = 'autocarros.CustomUser'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'autocarros',
    'django.contrib.humanize',
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # Adicionado para suporte a localização
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #'autocarros.middleware.PermissionMiddleware'
]

ROOT_URLCONF = 'gestao_autocarros.urls'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
		        'autocarros.context_processors.sectores_context',
            ],
        },
    },
]

# —— LOCALE / FORMATAÇÃO —— #
LANGUAGE_CODE = 'pt-PT'         # português europeu
TIME_ZONE = 'Africa/Luanda'

USE_I18N = True
USE_L10N = True
USE_TZ = True

# ⭐️ LIGA O SEPARADOR DE MILHAR
USE_THOUSAND_SEPARATOR = True

# Garante que o Django usa teus formatos personalizados em autocarros/locale/pt_PT/formats.py
FORMAT_MODULE_PATH = 'autocarros.locale'

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configurações de Autenticação
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# Níveis de acesso
GRUPOS = {
    'ADMIN': 'Administrador',
    'GESTOR': 'Gestor',
    'OPERADOR': 'Operador',
    'VISUALIZADOR': 'Visualizador',
}

# Configurações de sessão
SESSION_COOKIE_AGE = 3600  # 1 hora
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
