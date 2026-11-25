"""
Django settings for Antique Hub project.
Antique Hub: Premier Curated Heritage & Antique Marketplace

Configured for:
- Python 3.11+ / Django 5.x/6.x
- MySQL 8 with mysqlclient driver (credentials via .env)
- Role-based redirection (Admin, Seller, Buyer)
- Shared templates and static/media handling
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from django.contrib.messages import constants as messages

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

# Quick-start development settings - unsuitable for production
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-antique-hub-enterprise-secure-marketplace-key-2026')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if host.strip()]


# Application definition
INSTALLED_APPS = [
    # Django built-in core apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Antique Hub custom apps
    'accounts.apps.AccountsConfig',        # User profiles, authentication, roles (Admin, Seller, Buyer)
    'locations.apps.LocationsConfig',      # State, District, Location master data
    'catalog.apps.CatalogConfig',          # Category, SubCategory, Item listings
    'inventory.apps.InventoryConfig',      # Stock management & Category discounts
    'orders.apps.OrdersConfig',            # Shopping Cart, Purchase Master & Order Items
    'payments.apps.PaymentsConfig',        # Simulated payment gateway (PCI compliant sandbox)
    'community.apps.CommunityConfig',      # Item comments, Watchlist, FAQs
    'dashboard.apps.DashboardConfig',      # Custom Admin & Seller reporting dashboards
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'antique_hub.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],   # Shared root templates directory
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'community.context_processors.watchlist_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'antique_hub.wsgi.application'


# Database Configuration
# Uses MySQL 8 via mysqlclient by default, credentials managed strictly via .env
DB_ENGINE = os.getenv('DB_ENGINE', 'mysql').lower()

if DB_ENGINE == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('DB_NAME', 'antique_hub_db'),
            'USER': os.getenv('DB_USER', 'root'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', '127.0.0.1'),
            'PORT': os.getenv('DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (User uploaded antique photos, documents)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Authentication & Redirection URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:role_redirect'
LOGOUT_REDIRECT_URL = 'accounts:login'


# Django Messages Framework: map message levels to Bootstrap 5 alert classes
MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}
