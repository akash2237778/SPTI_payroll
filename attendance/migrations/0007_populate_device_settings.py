# Generated migration to populate initial DeviceSettings

from django.db import migrations
import os


def create_initial_device_settings(apps, schema_editor):
    """Create the initial DeviceSettings instance"""
    DeviceSettings = apps.get_model('attendance', 'DeviceSettings')
    
    # Get the IP from environment variable or use default
    device_ip = os.environ.get('ZK_DEVICE_IP', '192.168.2.66')
    
    # Create the singleton instance
    DeviceSettings.objects.get_or_create(
        pk=1,
        defaults={
            'device_ip': device_ip,
            'device_port': 4370,
            'timeout': 60,
            'password': 0,
            'force_udp': True,
            'ommit_ping': True,
        }
    )


def reverse_migration(apps, schema_editor):
    """Remove the DeviceSettings instance"""
    DeviceSettings = apps.get_model('attendance', 'DeviceSettings')
    DeviceSettings.objects.filter(pk=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0006_add_device_settings'),
    ]

    operations = [
        migrations.RunPython(create_initial_device_settings, reverse_migration),
    ]
