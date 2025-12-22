"""
Debug script to test the monthly report view and see what data it returns
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spti_payroll.settings')
django.setup()

from attendance.models import DailySummary, Employee
import datetime

def test_monthly_report_data(year=2025, month=11):
    """Test what the monthly report view would return"""
    
    print(f"Testing monthly report for {month}/{year}")
    print("=" * 80)
    
    # This is exactly what the view does
    summaries = DailySummary.objects.filter(
        date__year=year, 
        date__month=month
    ).select_related('employee').order_by('employee__name', 'date')
    
    print(f"Query returned {summaries.count()} summaries")
    
    # Process data in Python (same as view)
    report_map = {}
    
    for s in summaries:
        emp_id = s.employee.id
        if emp_id not in report_map:
            report_map[emp_id] = {
                'employee': s.employee,
                'days_present': 0,
                'total_hours': 0.0,
                'night_hours': 0.0,
                'overtime_hours': 0.0
            }
        
        data = report_map[emp_id]
        data['days_present'] += 1
        data['total_hours'] += float(s.total_hours)
        data['night_hours'] += float(s.night_hours)
        data['overtime_hours'] += float(s.overtime_hours)

    # Format for template
    report_data = []
    for emp_id, data in report_map.items():
        data['total_hours'] = round(data['total_hours'], 2)
        data['night_hours'] = round(data['night_hours'], 2)
        data['overtime_hours'] = round(data['overtime_hours'], 2)
        if data['days_present'] > 0:
            data['avg_hours'] = round(data['total_hours'] / data['days_present'], 2)
        else:
            data['avg_hours'] = 0.0
        report_data.append(data)
    
    print(f"\nProcessed {len(report_data)} employees")
    print("=" * 80)
    
    if report_data:
        print("\nEmployee Data:")
        print(f"{'Employee':<20} {'Days':<8} {'Total Hrs':<12} {'Avg Hrs':<10} {'OT Hrs':<10}")
        print("-" * 80)
        for data in report_data:
            print(f"{data['employee'].name:<20} {data['days_present']:<8} "
                  f"{data['total_hours']:<12.2f} {data['avg_hours']:<10.2f} "
                  f"{data['overtime_hours']:<10.2f}")
    else:
        print("\n⚠️  NO DATA FOUND - This is what the UI would show!")
    
    print("=" * 80)
    return report_data

if __name__ == '__main__':
    # Test November 2025
    data = test_monthly_report_data(2025, 11)
    
    if data:
        print(f"\n✅ SUCCESS: Found data for {len(data)} employees")
        print("\nThe view should be working. Possible issues:")
        print("  1. Web server needs to be restarted")
        print("  2. Browser cache needs to be cleared")
        print("  3. Different database being used (check DB_ENGINE in settings)")
    else:
        print("\n❌ PROBLEM: No data returned by view logic")
        print("This matches what you're seeing in the UI")
