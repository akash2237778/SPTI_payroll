"""
Helper script to analyze the attendance CSV and show which employees need to be created.

This script reads the CSV file and shows:
- Unique biometric IDs found in the CSV
- Count of attendance records per employee
- Date range for each employee
"""

import os
import sys
import csv
from datetime import datetime
from collections import defaultdict

def analyze_csv(csv_file_path):
    """Analyze the CSV file and show employee statistics."""
    print(f"Analyzing: {csv_file_path}")
    print("-" * 80)
    
    # Track employee data
    employee_data = defaultdict(lambda: {
        'count': 0,
        'dates': set(),
        'first_seen': None,
        'last_seen': None
    })
    
    october_november_only = defaultdict(lambda: {
        'count': 0,
        'dates': set(),
        'first_seen': None,
        'last_seen': None
    })
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                try:
                    user_id = int(row['UserID'])
                    timestamp_str = row['Timestamp'].strip()
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    
                    # All data
                    employee_data[user_id]['count'] += 1
                    employee_data[user_id]['dates'].add(timestamp.date())
                    if employee_data[user_id]['first_seen'] is None or timestamp < employee_data[user_id]['first_seen']:
                        employee_data[user_id]['first_seen'] = timestamp
                    if employee_data[user_id]['last_seen'] is None or timestamp > employee_data[user_id]['last_seen']:
                        employee_data[user_id]['last_seen'] = timestamp
                    
                    # October-November 2025 only
                    if timestamp.year == 2025 and timestamp.month in [10, 11]:
                        october_november_only[user_id]['count'] += 1
                        october_november_only[user_id]['dates'].add(timestamp.date())
                        if october_november_only[user_id]['first_seen'] is None or timestamp < october_november_only[user_id]['first_seen']:
                            october_november_only[user_id]['first_seen'] = timestamp
                        if october_november_only[user_id]['last_seen'] is None or timestamp > october_november_only[user_id]['last_seen']:
                            october_november_only[user_id]['last_seen'] = timestamp
                    
                except (ValueError, KeyError) as e:
                    continue
    
    except FileNotFoundError:
        print(f"ERROR: File not found: {csv_file_path}")
        return
    
    # Print all employees
    print("\n=== ALL EMPLOYEES IN CSV ===")
    print(f"Total unique employees: {len(employee_data)}")
    print(f"Biometric IDs: {sorted(employee_data.keys())}")
    print()
    
    print("Employee Details (All Data):")
    print(f"{'ID':<6} {'Records':<10} {'Days':<8} {'First Seen':<20} {'Last Seen':<20}")
    print("-" * 80)
    for emp_id in sorted(employee_data.keys()):
        data = employee_data[emp_id]
        print(f"{emp_id:<6} {data['count']:<10} {len(data['dates']):<8} "
              f"{data['first_seen'].strftime('%Y-%m-%d %H:%M'):<20} "
              f"{data['last_seen'].strftime('%Y-%m-%d %H:%M'):<20}")
    
    # Print October-November only
    print("\n" + "=" * 80)
    print("=== OCTOBER-NOVEMBER 2025 DATA ===")
    print(f"Total unique employees: {len(october_november_only)}")
    print(f"Biometric IDs: {sorted(october_november_only.keys())}")
    print()
    
    if october_november_only:
        print("Employee Details (Oct-Nov 2025 only):")
        print(f"{'ID':<6} {'Records':<10} {'Days':<8} {'First Seen':<20} {'Last Seen':<20}")
        print("-" * 80)
        for emp_id in sorted(october_november_only.keys()):
            data = october_november_only[emp_id]
            print(f"{emp_id:<6} {data['count']:<10} {len(data['dates']):<8} "
                  f"{data['first_seen'].strftime('%Y-%m-%d %H:%M'):<20} "
                  f"{data['last_seen'].strftime('%Y-%m-%d %H:%M'):<20}")
    
    # Generate Django commands to create employees
    print("\n" + "=" * 80)
    print("=== DJANGO COMMANDS TO CREATE EMPLOYEES ===")
    print("\nYou can create these employees using Django shell:")
    print("python manage.py shell\n")
    print("from attendance.models import Employee")
    print()
    
    for emp_id in sorted(october_november_only.keys()):
        print(f"Employee.objects.create(name='Employee {emp_id}', employee_id='EMP{emp_id:03d}', biometric_id={emp_id})")
    
    print("\n" + "=" * 80)
    print("\nOr use this bulk create command:")
    print("\nfrom attendance.models import Employee")
    print("employees = [")
    for emp_id in sorted(october_november_only.keys()):
        print(f"    Employee(name='Employee {emp_id}', employee_id='EMP{emp_id:03d}', biometric_id={emp_id}),")
    print("]")
    print("Employee.objects.bulk_create(employees)")
    print()


if __name__ == '__main__':
    csv_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'attendance_history.csv'
    )
    analyze_csv(csv_path)
