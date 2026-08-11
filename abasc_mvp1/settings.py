from pathlib import Path
import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}

def env_list(name: str, default: str = '') -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]

DEBUG = env_bool('DEBUG', True)
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-only-change-this-key').strip()
if not DEBUG and SECRET_KEY == 'dev-only-change-this-key':
    raise ImproperlyConfigured(
        'Defina uma SECRET_KEY segura antes de executar em produção.'
    )
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', '127.0.0.1,localhost')
CSRF_TRUSTED_ORIGINS = env_list(
    'CSRF_TRUSTED_ORIGINS',
    'http://127.0.0.1:8000,http://localhost:8000',
)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.core',
    'apps.accounts',
    'apps.news',
    'apps.associates',
    'apps.dashboards',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.accounts.middleware.LegacyOnboardingMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'abasc_mvp1.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'apps.core.context_processors.site_context',
        ],
    },
}]

WSGI_APPLICATION = 'abasc_mvp1.wsgi.application'
ASGI_APPLICATION = 'abasc_mvp1.asgi.application'

DATABASE_URL = os.getenv('DATABASE_URL', '').strip()
if not DEBUG and not DATABASE_URL:
    raise ImproperlyConfigured(
        'Defina DATABASE_URL para o PostgreSQL do Supabase em produção.'
    )
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=60,
            conn_health_checks=True,
            disable_server_side_cursors=True,
            ssl_require=env_bool('DB_SSL_REQUIRE', True),
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 7 * 1024 * 1024

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:post_login'
LOGOUT_REDIRECT_URL = 'core:home'

SUPABASE_URL = os.getenv('SUPABASE_URL', '').rstrip('/')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
SUPABASE_STORAGE_BUCKET_NEWS = os.getenv('SUPABASE_STORAGE_BUCKET_NEWS', 'abasc-news')
SUPABASE_STORAGE_BUCKET_AVATARS = os.getenv('SUPABASE_STORAGE_BUCKET_AVATARS', 'abasc-avatars')
ENABLE_LOCAL_AUTH = env_bool('ENABLE_LOCAL_AUTH', DEBUG)

if not DEBUG and not (SUPABASE_URL and SUPABASE_ANON_KEY):
    raise ImproperlyConfigured(
        'Defina SUPABASE_URL e SUPABASE_ANON_KEY em produção.'
    )

ABASC_CONTACT_EMAIL = os.getenv('ABASC_CONTACT_EMAIL', 'abasc.comunica@gmail.com')
ABASC_SITE_NAME = os.getenv('ABASC_SITE_NAME', 'ABASC')
ABASC_FULL_NAME = os.getenv(
    'ABASC_FULL_NAME',
    'Associação de Bacharéis em Saúde Coletiva',
)

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_SAVE_EVERY_REQUEST = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', False)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
# Cole estas configurações no final de config/settings.py.
# O arquivo já deve importar os.getenv ou import os.

SUPABASE_STORAGE_BUCKET_ASSOCIATIONS = os.getenv(
    "SUPABASE_STORAGE_BUCKET_ASSOCIATIONS",
    "abasc-associations",
)

ABASC_PIX_KEY = os.getenv(
    "ABASC_PIX_KEY",
    "35.848.139/0001-74",
)

ABASC_PIX_NAME = os.getenv(
    "ABASC_PIX_NAME",
    "Associação de Bacharéis em Saúde Coletiva",
)

ABASC_CONTACT_EMAIL = os.getenv(
    "ABASC_CONTACT_EMAIL",
    "diretoria@abascsaudecoletiva.com",
)

ABASC_CONTACT_PHONE = os.getenv(
    "ABASC_CONTACT_PHONE",
    "(61) 98158-3258",
)

ABASC_SITE_URL = os.getenv(
    "ABASC_SITE_URL",
    "http://127.0.0.1:8000",
)

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "diretoria@abascsaudecoletiva.com",
)