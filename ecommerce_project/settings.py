import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = '7u9#f2!s^q$e@w3B8pYhR*6Kz&XJdM%4C0A_LV+N' # Change in production

DEBUG = True

ALLOWED_HOSTS = ['testedovertime.pythonanywhere.com']

CSRF_TRUSTED_ORIGINS = ['https://testedovertime.pythonanywhere.com']

# Only use this if you're behind a proxy/load balancer
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'crispy_forms',
    'crispy_bootstrap5',

    # Local apps
    'shop.apps.ShopConfig',
    'accounts.apps.AccountsConfig',
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ecommerce_project.urls'

# Add to TEMPLATES
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),  # Make sure this is included
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ecommerce_project.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Custom user model
AUTH_USER_MODEL = 'accounts.CustomUser'

# Cart session settings
CART_SESSION_ID = 'cart'

LOGIN_REDIRECT_URL = 'shop:home'
LOGOUT_REDIRECT_URL = 'shop:home'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Or your email provider
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'forgivenessoverrevenge37@gmail.com'
EMAIL_HOST_PASSWORD = 'lfiw xjdd emjk eyso'
DEFAULT_FROM_EMAIL = 'forgivenessoverrevenge37@gmail.com'
SUPPORT_EMAIL = 'forgivenessoverrevenge37@gmail.com'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
