"""
Management command to reprocess all attendance summaries
"""
from django.core.management.base import BaseCommand
from attendance.models import AttendanceLog, DailySummary, Employee
from attendance.services import BiometricService
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Reprocess all attendance summaries from attendance logs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--from-date',
            type=str,
            help='Start date (YYYY-MM-DD). Defaults to 30 days ago',
        )
        parser.add_argument(
            '--to-date',
            type=str,
            help='End date (YYYY-MM-DD). Defaults to today',
        )
        parser.add_argument(
            '--employee-id',
            type=int,
            help='Process only specific employee ID',
        )
        parser.add_argument(
            '--delete-summaries',
            action='store_true',
            help='Delete existing summaries before reprocessing',
        )

    def handle(self, *args, **options):
        # Parse dates
        if options['from_date']:
            from_date = date.fromisoformat(options['from_date'])
        else:
            from_date = date.today() - timedelta(days=30)
        
        if options['to_date']:
            to_date = date.fromisoformat(options['to_date'])
        else:
            to_date = date.today()
        
        self.stdout.write(f"Reprocessing summaries from {from_date} to {to_date}")
        
        # Get employees
        if options['employee_id']:
            employees = Employee.objects.filter(id=options['employee_id'])
            if not employees.exists():
                self.stdout.write(self.style.ERROR(f"Employee ID {options['employee_id']} not found"))
                return
        else:
            employees = Employee.objects.all()
        
        self.stdout.write(f"Processing {employees.count()} employees")
        
        # Delete existing summaries if requested
        if options['delete_summaries']:
            deleted_count, _ = DailySummary.objects.filter(
                date__gte=from_date,
                date__lte=to_date
            ).delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted_count} existing summaries"))
        
        # Build list of affected keys
        affected_keys = []
        current_date = from_date
        while current_date <= to_date:
            for employee in employees:
                affected_keys.append((employee.id, current_date))
            current_date += timedelta(days=1)
        
        self.stdout.write(f"Processing {len(affected_keys)} employee-date combinations...")
        
        # Reprocess
        service = BiometricService()
        service._update_summaries(affected_keys)
        
        self.stdout.write(self.style.SUCCESS(f"✓ Reprocessed {len(affected_keys)} summaries"))
        
        # Show summary
        new_summaries = DailySummary.objects.filter(
            date__gte=from_date,
            date__lte=to_date
        ).count()
        self.stdout.write(self.style.SUCCESS(f"✓ Total summaries in date range: {new_summaries}"))
