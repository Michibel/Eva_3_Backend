"""
WSGI config for dulcearte project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dulcearte.settings.local')

application = get_wsgi_application()