"""
Django settings for openshift project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
import os
import imp


ON_OPENSHIFT = False
if os.environ.has_key('OPENSHIFT_REPO_DIR'):
     ON_OPENSHIFT = True

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY = 'ascq#%bii8(tld52#(^*ht@pzq%=nyb7fdv+@ok$u^iwb@2hwh'

default_keys = { 'SECRET_KEY': 'vm4rl5*ymb@2&d_(gc$gb-^twq9w(u69hi--%$5xrh!xk(t%hw' }
use_keys = default_keys

if ON_OPENSHIFT:
     imp.find_module('openshiftlibs')
     import openshiftlibs
     use_keys = openshiftlibs.openshift_secure(default_keys)

SECRET_KEY = use_keys['SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
if ON_OPENSHIFT:
     DEBUG = False
else:
     DEBUG = True

TEMPLATE_DEBUG = DEBUG

if DEBUG:
     ALLOWED_HOSTS = ['ultim-broquil.rhcloud.com']
else:
     ALLOWED_HOSTS = ['*']


DEBUG_TOOLBAR_CONFIG = {
    'JQUERY_URL':'',
}

# Application definition

INSTALLED_APPS = (
    #'suit',
    'django_admin_bootstrapped.bootstrap3',
    'django_admin_bootstrapped',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'elbroquil',
    'formadmin',
    'django_tables2',
    'xlrd',
    'xlutils',
    'rosetta',
    'bootstrapform',
    'debug_toolbar',
    'chroniker',
    'suit_redactor',
    'mathfilters',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

# If you want configure the REDISCLOUD
if 'REDISCLOUD_URL' in os.environ and 'REDISCLOUD_PORT' in os.environ and 'REDISCLOUD_PASSWORD' in os.environ:
    redis_server = os.environ['REDISCLOUD_URL']
    redis_port = os.environ['REDISCLOUD_PORT']
    redis_password = os.environ['REDISCLOUD_PASSWORD']
    CACHES = {
        'default' : {
            'BACKEND' : 'redis_cache.RedisCache',
            'LOCATION' : '%s:%d'%(redis_server,int(redis_port)),
            'OPTIONS' : {
                'DB':0,
                'PARSER_CLASS' : 'redis.connection.HiredisParser',
                'PASSWORD' : redis_password,
            }
        }
    }
    MIDDLEWARE_CLASSES = ('django.middleware.cache.UpdateCacheMiddleware',) + MIDDLEWARE_CLASSES + ('django.middleware.cache.FetchFromCacheMiddleware',)

ROOT_URLCONF = 'urls'

WSGI_APPLICATION = 'wsgi.application'

TEMPLATE_DIRS = (
     os.path.join(BASE_DIR,'templates'),
     os.path.join(BASE_DIR,'elbroquil/templates'),
)

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases
if ON_OPENSHIFT:
     DATABASES = {
         'default': {
             'ENGINE': 'django.db.backends.mysql',
             'NAME': os.environ['OPENSHIFT_APP_NAME'],
             'USER': os.environ['OPENSHIFT_MYSQL_DB_USERNAME'],             # Not used with sqlite3.
             'PASSWORD': os.environ['OPENSHIFT_MYSQL_DB_PASSWORD'],         # Not used with sqlite3.
             'HOST': os.environ['OPENSHIFT_MYSQL_DB_HOST'],             # Set to empty string for localhost. Not used with sqlite3.
             'PORT': os.environ['OPENSHIFT_MYSQL_DB_PORT'],             # Set to empty string for default. Not used with sqlite3.
         }
     }
else:
     DATABASES = {
         'default': {
             'ENGINE': 'django.db.backends.mysql',
             'NAME': os.environ['DB_NAME'],
             'USER': os.environ['DB_USERNAME'],             # Not used with sqlite3.
             'PASSWORD': os.environ['DB_PASSWORD'],         # Not used with sqlite3.
             'HOST': '127.0.0.1',             # Set to empty string for localhost. Not used with sqlite3.
             'PORT': '3306',             # Set to empty string for default. Not used with sqlite3.
         }
     }
     #DATABASES = {
     #    'default':{
     #        'ENGINE': 'django.db.backends.sqlite3',
     #        'NAME': './broquil.db',
	 #   }
	#}
    #DATABASES = {
    #    'default': {
    #        'ENGINE': 'django.db.backends.postgresql_psycopg2',
    #        'NAME': 'elbroquil_ultim2',
    #        'USER': 'onur2',
    #        'PASSWORD': '12345',
    #        'HOST': 'localhost',
    #        'PORT': '5432',
    #    }
    #}

# Email settings
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = os.environ['EMAIL_HOST_USER']
EMAIL_HOST_PASSWORD = os.environ['EMAIL_HOST_PASSWORD']
EMAIL_PORT = 587

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'ca'

TIME_ZONE = 'Europe/Madrid'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
    #os.path.join(BASE_DIR, 'elbroquil/locale'),
)

LANGUAGES = (
    ('tr', _('Turkish')),
    ('ca', _('Catala')),
    ('es', _('Castellano')),
    ('en', _('English')),
)
# Allow all host headers
ALLOWED_HOSTS = ['*']

LOGIN_REDIRECT_URL = '/'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
if ON_OPENSHIFT:
    STATIC_ROOT = os.path.join(BASE_DIR, '..', 'static')
    STATIC_URL = '/static/'

else:
    STATIC_ROOT = 'staticfiles'
    STATIC_URL = '/static/'
    
    STATICFILES_DIRS = (
        os.path.join(BASE_DIR, '..', 'static'),
    )

from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS as TCP

TEMPLATE_CONTEXT_PROCESSORS = TCP + (
    'django.core.context_processors.request',
    'django.core.context_processors.i18n',
)

if ON_OPENSHIFT:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
            },
            'simple': {
                'format': '%(levelname)s %(message)s'
            },
        },
        'handlers': {
            'file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': os.environ['OPENSHIFT_HOMEDIR']+'/app-root/logs/broquil.log',
            },
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'simple'
            },
        },
        'loggers': {
            'django.request': {
                'handlers': ['file'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'custom': {
                'handlers': ['console'],
                'level': 'DEBUG',
                'propagate': True,
            },
        },
    }
