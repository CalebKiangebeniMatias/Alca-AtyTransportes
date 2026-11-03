
from pathlib import Path
import os
import dj_database_url

from django.core.management.utils import get_random_secret_key


# =====================================================
# 1. DIRETÓRIO BASE
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# =====================================================
# 2. SEGURANÇA E AMBIENTE
# =====================================================

# Em produção, configura SECRET_KEY nas variáveis do Render.
SECRET_KEY = os.getenv('SECRET_KEY')

if not SECRET_KEY:
    if os.getenv('RENDER'):
        raise RuntimeError(
            "A variável SECRET_KEY não está configurada no Render."
        )
    SECRET_KEY = get_random_secret_key()


# DEBUG fica desativado automaticamente no Render.
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

if os.getenv('RENDER'):
    DEBUG = False


# =====================================================
# 3. HOSTS PERMITIDOS
# =====================================================

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    '0.0.0.0',
    'alca-atytransportes.onrender.com',
    'alca-atytransportes-aouf.onrender.com',
]

# Adiciona automaticamente o domínio fornecido pelo Render.
RENDER_HOST = os.getenv('RENDER_EXTERNAL_HOSTNAME')

if RENDER_HOST and RENDER_HOST not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_HOST)


# =====================================================
# 4. CSRF
# =====================================================

CSRF_TRUSTED_ORIGINS = [
    'https://alca-atytransportes.onrender.com',
    'https://alca-atytransportes-aouf.onrender.com',
    'http://localhost',
    'http://127.0.0.1',
]

# Domínio personalizado, se existir.
CUSTOM_DOMAIN = os.getenv('CUSTOM_DOMAIN')

if CUSTOM_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(
        f'https://{CUSTOM_DOMAIN}'
    )


# =====================================================
# 5. CONFIGURAÇÕES HTTPS
# =====================================================

SECURE_PROXY_SSL_HEADER = (
    'HTTP_X_FORWARDED_PROTO',
    'https'
)

SECURE_SSL_REDIRECT = not DEBUG

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'


# =====================================================
# 6. UTILIZADOR PERSONALIZADO
# =====================================================

AUTH_USER_MODEL = 'autocarros.CustomUser'


# =====================================================
# 7. BANCO DE DADOS
# =====================================================

DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=True,
        )
    }

else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# =====================================================
# 8. FUSO HORÁRIO E IDIOMA
# =====================================================

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'Africa/Luanda'

USE_I18N = True
USE_TZ = True

USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = '.'
DECIMAL_SEPARATOR = ','


# =====================================================
# 9. FICHEIROS MEDIA
# =====================================================

MEDIA_URL = '/media/'

MEDIA_ROOT = Path(
    os.getenv('MEDIA_ROOT', str(BASE_DIR / 'media'))
)


# =====================================================
# 10. FICHEIROS ESTÁTICOS
# =====================================================

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATIC_ROOT = BASE_DIR / 'staticfiles'


# =====================================================
# 11. WHITE NOISE
# =====================================================

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': (
            'whitenoise.storage.'
            'CompressedManifestStaticFilesStorage'
        ),
    },
}


# =====================================================
# 12. AUTENTICAÇÃO
# =====================================================

LOGIN_URL = '/login/'

LOGIN_REDIRECT_URL = '/dashboard/'

LOGOUT_REDIRECT_URL = '/login/'


# =====================================================
# 13. APLICAÇÕES
# =====================================================

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


# =====================================================
# 14. MIDDLEWARE
# =====================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',

    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',

    'django.middleware.locale.LocaleMiddleware',

    'django.middleware.common.CommonMiddleware',

    'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',

    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# =====================================================
# 15. URLS
# =====================================================

ROOT_URLCONF = 'gestao_autocarros.urls'


# =====================================================
# 16. TEMPLATES
# =====================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',

        'DIRS': [
            BASE_DIR / 'templates',
        ],

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


# =====================================================
# 17. DEFAULT AUTO FIELD
# =====================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
