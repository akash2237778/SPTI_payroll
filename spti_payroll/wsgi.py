import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spti_payroll.settings')

application = get_wsgi_application()
