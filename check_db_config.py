import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spti_payroll.settings')
django.setup()

from django.conf import settings

print("Database Configuration:")
print(f"  Engine: {settings.DATABASES['default']['ENGINE']}")
print(f"  Name: {settings.DATABASES['default']['NAME']}")

if 'sqlite' in settings.DATABASES['default']['ENGINE']:
    db_path = settings.DATABASES['default']['NAME']
    if os.path.exists(db_path):
        size = os.path.getsize(db_path) / 1024 / 1024
        print(f"  Size: {size:.2f} MB")
        print(f"  Path: {db_path}")
    else:
        print(f"  WARNING: Database file does not exist!")
