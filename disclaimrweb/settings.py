"""
Django settings for disclaimrweb project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import glob
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DEBUG = True

ALLOWED_HOSTS = ["0.0.0.0/0"]

# Application definition

INSTALLED_APPS = (
    'grappelli',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'disclaimrwebadmin',
    'adminsortable2'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'disclaimrweb.urls'

WSGI_APPLICATION = 'disclaimrweb.wsgi.application'


# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = ''
MEDIA_ROOT = ''

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.FileSystemFinder',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # insert your TEMPLATE_DIRS here
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

GRAPPELLI_ADMIN_TITLE = "DisclaimR Web Administration"

# Import local settings

conffiles = glob.glob(os.path.join(BASE_DIR, "settings", "*.conf"))
conffiles.sort()
for f in conffiles:
    execfile(os.path.abspath(f))

# Generate a SECRET_KEY if it hasn't been already set.
# Taken from https://gist.github.com/ndarville/3452907

try:
    SECRET_KEY
except NameError:
    SECRET_FILE = os.path.join(BASE_DIR, "secret.txt")
    try:
        SECRET_KEY = open(SECRET_FILE).read().strip()
    except IOError:
        try:
            import random
            SECRET_KEY = "".join(
                [random.SystemRandom().choice(
                    "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
                ) for i in range(50)]
            )
            secret = file(SECRET_FILE, "w")
            secret.write(SECRET_KEY)
            secret.close()
        except IOError:
            Exception("Please create a %s file with random characters to "
                      "generate your secret key!" % SECRET_FILE)
