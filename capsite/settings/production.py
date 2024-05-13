from .base import *

try:
    from .local import *
except ImportError:
    pass

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

DEBUG = env('DEBUG', False)

WAGTAIL_ENABLE_UPDATE_CHECK = False
