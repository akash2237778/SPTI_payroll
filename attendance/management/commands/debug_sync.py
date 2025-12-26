from django.core.management.base import BaseCommand
from django.conf import settings
from attendance.models import Employee, AttendanceLog, DailySummary
from attendance.services import BiometricService
from django.utils import timezone
import datetime

class Command(BaseCommand):
    help = 'Debugs attendance data and forces a sync'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(f"Current Timezone: {timezone.get_current_timezone_name()}"))
        
        # 1. Pre-Sync Stats
        self.print_stats("PRE-SYNC")

        # 2. Run Sync
        from attendance.models import DeviceSettings
        device_settings = DeviceSettings.get_settings()
        ip = device_settings.device_ip

        self.stdout.write(self.style.SUCCESS(f"Starting Sync with {ip}..."))
        try:
            service = BiometricService()
            service.sync_device()  # Will use DeviceSettings automatically
            self.stdout.write(self.style.SUCCESS("Sync Completed."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Sync Failed: {e}"))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))

        # 3. Post-Sync Stats
        self.print_stats("POST-SYNC")

    def print_stats(self, label):
        self.stdout.write(self.style.MIGRATE_HEADING(f"--- {label} STATS ---"))
        
        emp_count = Employee.objects.count()
        log_count = AttendanceLog.objects.count()
        summary_count = DailySummary.objects.count()
        
        self.stdout.write(f"Employees: {emp_count}")
        self.stdout.write(f"Total Logs: {log_count}")
        self.stdout.write(f"Total Summaries: {summary_count}")

        # Check Nov 2025 specifically
        start_date = datetime.date(2025, 11, 1)
        end_date = datetime.date(2025, 11, 30)
        
        logs_nov = AttendanceLog.objects.filter(timestamp__date__range=(start_date, end_date)).count()
        sums_nov = DailySummary.objects.filter(date__range=(start_date, end_date)).count()
        
        self.stdout.write(f"Nov 2025 Logs: {logs_nov}")
        self.stdout.write(f"Nov 2025 Summaries: {sums_nov}")

        if logs_nov > 0 and sums_nov == 0:
            self.stdout.write(self.style.WARNING("WARNING: Logs exist for Nov 2025 but NO Summaries!"))
            
        # Sample
        if sums_nov > 0:
            sample = DailySummary.objects.filter(date__range=(start_date, end_date)).first()
            self.stdout.write(f"Sample Summary: {sample} - Hours: {sample.total_hours}")
