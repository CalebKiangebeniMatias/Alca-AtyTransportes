from pathlib import Path
import os
try:
    from django.core.management.utils import get_random_secret_key
except ImportError:
    from django.core.management.base import get_random_secret_key
import dj_database_url  # garante que você importou

BASE_DIR = Path(__file__).resolve().parent.parent

# 🔹 Chave e Debug
SECRET_KEY = os.getenv('SECRET_KEY', get_random_secret_key())

DEBUG = True

# 🔹 Hosts permitidos
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '0.0.0.0', 'alca-atytransportes.onrender.com']


# settings.py
AUTH_USER_MODEL = 'autocarros.CustomUser'

# 🔹 Banco de dados
if os.getenv('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.parse(
            os.getenv('DATABASE_URL'),
            conn_max_age=600,
            ssl_require=True
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# 🔹 Media e static
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# 🔹 Autenticação
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# 🔹 Localização / formatação de números
LANGUAGE_CODE = 'pt-br'
USE_I18N = True
USE_L10N = True
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = '.'
DECIMAL_SEPARATOR = ','

# 🔹 Installed apps, middleware, templates...
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

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gestao_autocarros.urls'

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
