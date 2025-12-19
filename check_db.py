import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spti_payroll.settings')
django.setup()

from attendance.models import Employee, AttendanceLog, DailySummary
import datetime

print(f'Employees: {Employee.objects.count()}')
print(f'Total Logs: {AttendanceLog.objects.count()}')

nov_logs = AttendanceLog.objects.filter(
    timestamp__date__gte=datetime.date(2025, 11, 1),
    timestamp__date__lte=datetime.date(2025, 11, 30)
)
print(f'Nov 2025 Logs: {nov_logs.count()}')

nov_sums = DailySummary.objects.filter(
    date__gte=datetime.date(2025, 11, 1),
    date__lte=datetime.date(2025, 11, 30)
)
print(f'Nov 2025 Summaries: {nov_sums.count()}')

if nov_logs.exists():
    print('\nSample Nov 2025 logs:')
    for log in nov_logs[:5]:
        print(f'  {log.employee.name} - {log.timestamp}')

if nov_sums.exists():
    print('\nSample Nov 2025 summaries:')
    for s in nov_sums[:5]:
        print(f'  {s.employee.name} - {s.date} - {s.total_hours}h')

# Check all logs date range
if AttendanceLog.objects.exists():
    first_log = AttendanceLog.objects.order_by('timestamp').first()
    last_log = AttendanceLog.objects.order_by('-timestamp').first()
    print(f'\nLog date range: {first_log.timestamp} to {last_log.timestamp}')
