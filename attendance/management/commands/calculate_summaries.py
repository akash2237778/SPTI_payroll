"""
Management command to calculate daily summaries from attendance logs.

This is useful after importing historical data or when summaries need to be recalculated.

Usage:
    python manage.py calculate_summaries
    python manage.py calculate_summaries --start-date 2025-10-01 --end-date 2025-12-31
    python manage.py calculate_summaries --employee-id 1
"""

from django.core.management.base import BaseCommand
from django.db.models import Min, Max
from attendance.models import AttendanceLog, DailySummary, Employee
from attendance.services import BiometricService
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Calculate daily summaries from attendance logs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date (YYYY-MM-DD). If not provided, uses earliest log date.'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date (YYYY-MM-DD). If not provided, uses latest log date.'
        )
        parser.add_argument(
            '--employee-id',
            type=int,
            help='Process only specific employee ID (biometric_id)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Recalculate even if summaries already exist'
        )

    def handle(self, *args, **options):
        self.stdout.write("Calculating daily summaries from attendance logs...")
        self.stdout.write("=" * 80)
        
        # Get date range
        if options['start_date']:
            start_date = datetime.strptime(options['start_date'], '%Y-%m-%d').date()
        else:
            start_date = AttendanceLog.objects.aggregate(Min('timestamp'))['timestamp__min']
            if start_date:
                start_date = start_date.date()
            else:
                self.stdout.write(self.style.WARNING("No attendance logs found"))
                return
        
        if options['end_date']:
            end_date = datetime.strptime(options['end_date'], '%Y-%m-%d').date()
        else:
            end_date = AttendanceLog.objects.aggregate(Max('timestamp'))['timestamp__max']
            if end_date:
                end_date = end_date.date()
            else:
                end_date = start_date
        
        self.stdout.write(f"Date range: {start_date} to {end_date}")
        
        # Get employees
        if options['employee_id']:
            employees = Employee.objects.filter(biometric_id=options['employee_id'])
            if not employees.exists():
                self.stdout.write(self.style.ERROR(f"Employee with biometric_id {options['employee_id']} not found"))
                return
        else:
            employees = Employee.objects.all()
        
        self.stdout.write(f"Processing {employees.count()} employee(s)")
        self.stdout.write("=" * 80)
        
        # Collect all affected (employee, date) pairs
        affected_keys = set()
        
        for employee in employees:
            # Get all logs for this employee in the date range
            logs = AttendanceLog.objects.filter(
                employee=employee,
                timestamp__date__gte=start_date,
                timestamp__date__lte=end_date
            ).order_by('timestamp')
            
            if not logs.exists():
                continue
            
            # Get unique dates
            dates = logs.values_list('timestamp__date', flat=True).distinct()
            
            for log_date in dates:
                affected_keys.add((employee.id, log_date))
            
            self.stdout.write(f"  {employee.name}: {len(dates)} day(s) with attendance")
        
        if not affected_keys:
            self.stdout.write(self.style.WARNING("No attendance data found in the specified range"))
            return
        
        self.stdout.write("=" * 80)
        self.stdout.write(f"Total days to process: {len(affected_keys)}")
        
        # Use BiometricService to calculate summaries
        service = BiometricService()
        
        self.stdout.write("\nCalculating summaries...")
        service._update_summaries(affected_keys)
        
        # Show results
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("Summary calculation complete!"))
        
        # Show statistics
        total_summaries = DailySummary.objects.count()
        self.stdout.write(f"\nTotal daily summaries in database: {total_summaries}")
        
        # Show breakdown by month
        from django.db.models import Count
        from django.db.models.functions import TruncMonth
        
        monthly_counts = DailySummary.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        if monthly_counts:
            self.stdout.write("\nSummaries by month:")
            for item in monthly_counts:
                month_str = item['month'].strftime('%B %Y')
                self.stdout.write(f"  {month_str}: {item['count']} summaries")
