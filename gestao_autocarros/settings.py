from pathlib import Path
import os
from django.core.management.utils import get_random_secret_key
import dj_database_url
from dotenv import load_dotenv

# ─── BASE DIR ───
BASE_DIR = Path(__file__).resolve().parent.parent

# ─── LOAD ENV ───
# Carrega explicitamente o .env
dotenv_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path)

# ─── MEDIA ───
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ─── SECRET KEY & DEBUG ───
SECRET_KEY = os.getenv('SECRET_KEY', get_random_secret_key())
DEBUG = os.getenv('DEBUG', 'True') == 'True'

# ─── HOSTS ───
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

# ─── USER MODEL ───
AUTH_USER_MODEL = 'autocarros.CustomUser'

# ─── APPS ───
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'autocarros',
]

# ─── MIDDLEWARE ───
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ✅ necessário no Render
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ─── URLS ───
ROOT_URLCONF = 'gestao_autocarros.urls'


import dj_database_url

DATABASES = {
    'default': dj_database_url.parse(
        'postgresql://banco_alca_aty_user:UtoSBIAyRykAzpFtDAF8jUfRSaVumUUR@dpg-d3hj6iffte5s73d08ovg-a.oregon-postgres.render.com/banco_alca_aty',
        conn_max_age=600,
        ssl_require=True  # Render exige SSL
    )
}


# ─── TEMPLATES ───
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

# ─── LOCALE / FORMATOS ───
LANGUAGE_CODE = 'pt-PT'
TIME_ZONE = 'Africa/Luanda'
USE_I18N = True
USE_L10N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True
FORMAT_MODULE_PATH = 'autocarros.locale'

# ─── STATIC ───
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"  # ✅

# ─── AUTENTICAÇÃO ───
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# ─── GRUPOS ───
GRUPOS = {
    'ADMIN': 'Administrador',
    'GESTOR': 'Gestor',
    'OPERADOR': 'Operador',
    'VISUALIZADOR': 'Visualizador',
}

# ─── SESSÃO ───
SESSION_COOKIE_AGE = 3600
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# ─── SEGURANÇA PARA PRODUÇÃO ───
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
