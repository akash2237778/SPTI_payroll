"""
Script to create employees based on the biometric IDs found in attendance_history.csv

This should be run BEFORE populate_attendance_history.py
"""

import os
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spti_payroll.settings')

import django
django.setup()

from attendance.models import Employee

# Biometric IDs found in Oct-Nov-Dec 2025 data from the CSV
EMPLOYEES_TO_CREATE = [
    (1, 'Employee 1', 'EMP001'),
    (2, 'Employee 2', 'EMP002'),
    (4, 'Employee 4', 'EMP004'),
    (6, 'Employee 6', 'EMP006'),
    (7, 'Employee 7', 'EMP007'),
    (8, 'Employee 8', 'EMP008'),
    (9, 'Employee 9', 'EMP009'),
    (10, 'Employee 10', 'EMP010'),
    (11, 'Employee 11', 'EMP011'),
    (12, 'Employee 12', 'EMP012'),
    (15, 'Employee 15', 'EMP015'),
    (17, 'Employee 17', 'EMP017'),
    (18, 'Employee 18', 'EMP018'),
    (19, 'Employee 19', 'EMP019'),
    (20, 'Employee 20', 'EMP020'),
    (21, 'Employee 21', 'EMP021'),
    (23, 'Employee 23', 'EMP023'),
    (24, 'Employee 24', 'EMP024'),
    (25, 'Employee 25', 'EMP025'),
    (26, 'Employee 26', 'EMP026'),
    (28, 'Employee 28', 'EMP028'),
    (29, 'Employee 29', 'EMP029'),
    (30, 'Employee 30', 'EMP030'),
    (31, 'Employee 31', 'EMP031'),
    (32, 'Employee 32', 'EMP032'),
    (33, 'Employee 33', 'EMP033'),
    (44, 'Employee 44', 'EMP044'),
    (55, 'Employee 55', 'EMP055'),
    (9999, 'Test Employee', 'EMP9999'),
]

def create_employees():
    """Create employees if they don't exist."""
    print("Creating employees...")
    print("-" * 80)
    
    created_count = 0
    skipped_count = 0
    
    for biometric_id, name, employee_id in EMPLOYEES_TO_CREATE:
        # Check if employee already exists
        if Employee.objects.filter(biometric_id=biometric_id).exists():
            print(f"⏭️  Skipped: {name} (biometric_id={biometric_id}) - already exists")
            skipped_count += 1
            continue
        
        # Create employee
        employee = Employee.objects.create(
            name=name,
            employee_id=employee_id,
            biometric_id=biometric_id,
            working_hours=8.0
        )
        print(f"✅ Created: {employee.name} (biometric_id={employee.biometric_id})")
        created_count += 1
    
    print("-" * 80)
    print(f"Summary:")
    print(f"  Created: {created_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Total:   {created_count + skipped_count}")
    print("-" * 80)
    
    # Verify
    total_employees = Employee.objects.count()
    print(f"Total employees in database: {total_employees}")
    print("\nEmployees created successfully! You can now run:")
    print("  python populate_attendance_history.py")

if __name__ == '__main__':
    create_employees()
