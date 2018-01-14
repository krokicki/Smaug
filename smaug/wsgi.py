import os
import sys

sys.path.append('/var/www/smaug')

os.environ['DJANGO_SETTINGS_MODULE'] = 'web_settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

