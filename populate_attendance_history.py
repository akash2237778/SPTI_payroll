"""
Script to populate historical attendance data from CSV file to database.

This script reads attendance_history.csv and populates the AttendanceLog table.
It handles:
- Mapping biometric IDs to employees
- Parsing timestamps
- Avoiding duplicates
- Filtering by date range (October, November, December 2025)
- Transaction-based bulk inserts for performance
"""

import os
import sys
import csv
from datetime import datetime
from django.db import transaction
from django.utils import timezone

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spti_payroll.settings')

import django
django.setup()

from attendance.models import Employee, AttendanceLog


def parse_timestamp(timestamp_str):
    """Parse timestamp string to datetime object."""
    try:
        # Format: 2025-10-01 08:38:52
        return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
    except ValueError as e:
        print(f"Error parsing timestamp '{timestamp_str}': {e}")
        return None


def filter_october_november_december(timestamp):
    """Check if timestamp is in October, November, or December 2025."""
    if timestamp is None:
        return False
    return timestamp.year == 2025 and timestamp.month in [10, 11, 12]


def populate_attendance_history(csv_file_path, dry_run=False):
    """
    Populate attendance history from CSV file.
    
    Args:
        csv_file_path: Path to the CSV file
        dry_run: If True, don't actually save to database (for testing)
    """
    print(f"Starting attendance history population from: {csv_file_path}")
    print(f"Dry run mode: {dry_run}")
    print("-" * 80)
    
    # Statistics
    stats = {
        'total_rows': 0,
        'filtered_out': 0,  # Not in Oct-Nov-Dec range
        'invalid_timestamp': 0,
        'employee_not_found': 0,
        'duplicates_skipped': 0,
        'successfully_created': 0,
        'errors': 0
    }
    
    # Get all employees and create a mapping of biometric_id -> Employee
    employees = Employee.objects.all()
    employee_map = {emp.biometric_id: emp for emp in employees}
    print(f"Found {len(employee_map)} employees in database")
    print(f"Biometric IDs: {sorted(employee_map.keys())}")
    print("-" * 80)
    
    # Track unique entries to avoid duplicates within the CSV
    seen_entries = set()
    
    # Collect logs to be created
    logs_to_create = []
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                stats['total_rows'] += 1
                
                # Parse row data
                try:
                    user_id = int(row['UserID'])
                    timestamp_str = row['Timestamp'].strip()
                    # Status is not needed for this application, always use 0
                    status = 0
                except (ValueError, KeyError) as e:
                    print(f"Error parsing row {stats['total_rows']}: {e}")
                    stats['errors'] += 1
                    continue
                
                # Parse timestamp
                timestamp = parse_timestamp(timestamp_str)
                if timestamp is None:
                    stats['invalid_timestamp'] += 1
                    continue
                
                # Filter by date range (October-November-December 2025)
                if not filter_october_november_december(timestamp):
                    stats['filtered_out'] += 1
                    continue
                
                # Find employee by biometric_id
                employee = employee_map.get(user_id)
                if employee is None:
                    if stats['employee_not_found'] < 10:  # Only print first 10
                        print(f"Warning: Employee with biometric_id {user_id} not found (timestamp: {timestamp_str})")
                    stats['employee_not_found'] += 1
                    continue
                
                # Create unique key to detect duplicates
                unique_key = (employee.id, timestamp)
                if unique_key in seen_entries:
                    stats['duplicates_skipped'] += 1
                    continue
                
                seen_entries.add(unique_key)
                
                # Create AttendanceLog object (but don't save yet)
                log = AttendanceLog(
                    employee=employee,
                    timestamp=timestamp,
                    status=status,
                    verification_mode=1  # Default verification mode
                )
                logs_to_create.append(log)
                
                # Progress indicator
                if len(logs_to_create) % 100 == 0:
                    print(f"Processed {stats['total_rows']} rows, prepared {len(logs_to_create)} logs...")
        
        print("-" * 80)
        print(f"CSV parsing complete. Prepared {len(logs_to_create)} attendance logs.")
        print("-" * 80)
        
        # Bulk create logs in database (if not dry run)
        if not dry_run and logs_to_create:
            print("Saving to database...")
            
            # Check for existing logs to avoid database-level duplicates
            existing_logs = set()
            for log in logs_to_create:
                existing = AttendanceLog.objects.filter(
                    employee=log.employee,
                    timestamp=log.timestamp
                ).exists()
                if existing:
                    existing_logs.add((log.employee.id, log.timestamp))
            
            # Filter out existing logs
            logs_to_create = [
                log for log in logs_to_create 
                if (log.employee.id, log.timestamp) not in existing_logs
            ]
            
            stats['duplicates_skipped'] += len(existing_logs)
            
            print(f"After checking database, {len(logs_to_create)} new logs to create...")
            
            # Bulk create in transaction
            with transaction.atomic():
                created_logs = AttendanceLog.objects.bulk_create(
                    logs_to_create,
                    batch_size=500,
                    ignore_conflicts=True  # Ignore any remaining duplicates
                )
                stats['successfully_created'] = len(created_logs)
            
            print(f"Successfully created {stats['successfully_created']} attendance logs!")
        else:
            stats['successfully_created'] = len(logs_to_create)
            if dry_run:
                print("DRY RUN - No data was saved to database")
    
    except FileNotFoundError:
        print(f"ERROR: File not found: {csv_file_path}")
        return
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Print statistics
    print("-" * 80)
    print("STATISTICS:")
    print(f"  Total rows in CSV:           {stats['total_rows']}")
    print(f"  Filtered out (not Oct-Dec):  {stats['filtered_out']}")
    print(f"  Invalid timestamps:          {stats['invalid_timestamp']}")
    print(f"  Employee not found:          {stats['employee_not_found']}")
    print(f"  Duplicates skipped:          {stats['duplicates_skipped']}")
    print(f"  Successfully created:        {stats['successfully_created']}")
    print(f"  Errors:                      {stats['errors']}")
    print("-" * 80)
    
    # Show date range of imported data
    if logs_to_create:
        timestamps = [log.timestamp for log in logs_to_create]
        min_date = min(timestamps)
        max_date = max(timestamps)
        print(f"Date range: {min_date.date()} to {max_date.date()}")
        print("-" * 80)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Populate attendance history from CSV')
    parser.add_argument(
        '--csv',
        default='attendance_history.csv',
        help='Path to CSV file (default: attendance_history.csv)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without saving to database (for testing)'
    )
    
    args = parser.parse_args()
    
    # Get absolute path
    csv_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        args.csv
    )
    
    populate_attendance_history(csv_path, dry_run=args.dry_run)
