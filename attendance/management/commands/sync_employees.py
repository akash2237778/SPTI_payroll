"""
Management command to sync employees from the ZK biometric device.

Usage:
    python manage.py sync_employees
    python manage.py sync_employees --ip 192.168.2.66
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from attendance.services import BiometricService
from attendance.models import Employee
from zk import ZK


class Command(BaseCommand):
    help = 'Sync employees from ZK biometric device'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ip',
            type=str,
            default=settings.ZK_DEVICE_IP,
            help='IP address of the ZK device (default: from settings)'
        )
        parser.add_argument(
            '--port',
            type=int,
            default=4370,
            help='Port of the ZK device (default: 4370)'
        )

    def handle(self, *args, **options):
        ip = options['ip']
        port = options['port']
        
        self.stdout.write(f"Connecting to ZK device at {ip}:{port}...")
        
        zk = ZK(ip, port=port, timeout=5, password=0, force_udp=False, ommit_ping=False)
        conn = None
        
        try:
            conn = zk.connect()
            self.stdout.write(self.style.SUCCESS(f"✓ Connected to device"))
            
            # Get users from device
            self.stdout.write("Fetching users from device...")
            users = conn.get_users()
            self.stdout.write(f"Found {len(users)} users on device")
            
            if not users:
                self.stdout.write(self.style.WARNING("No users found on device"))
                return
            
            # Show users
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write("Users on device:")
            self.stdout.write(f"{'UID':<8} {'Badge ID':<15} {'Name':<30}")
            self.stdout.write("-" * 80)
            for user in users:
                self.stdout.write(f"{user.uid:<8} {user.user_id:<15} {user.name:<30}")
            
            # Sync to database
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write("Syncing to database...")
            
            created_count = 0
            updated_count = 0
            
            for user in users:
                employee, created = Employee.objects.update_or_create(
                    biometric_id=user.uid,
                    defaults={
                        'name': user.name,
                        'employee_id': user.user_id,
                        'working_hours': 8.0
                    }
                )
                
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Created: {employee.name} (biometric_id={employee.biometric_id})")
                    )
                    created_count += 1
                else:
                    self.stdout.write(
                        f"  Updated: {employee.name} (biometric_id={employee.biometric_id})"
                    )
                    updated_count += 1
            
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.SUCCESS(f"Summary:"))
            self.stdout.write(f"  Created: {created_count}")
            self.stdout.write(f"  Updated: {updated_count}")
            self.stdout.write(f"  Total:   {created_count + updated_count}")
            
            # Show total in database
            total_employees = Employee.objects.count()
            self.stdout.write(f"\nTotal employees in database: {total_employees}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            import traceback
            traceback.print_exc()
        finally:
            if conn:
                conn.disconnect()
                self.stdout.write("\nDisconnected from device")
