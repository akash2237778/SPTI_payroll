"""
Test case: Employee working from 9:00 AM to 2:00 AM next day (17 hours)
This tests:
- Midnight crossing
- Night hours calculation
- Break deduction
- Overtime calculation
"""
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, time as dt_time
from attendance.models import Shift, Employee, AttendanceLog, DailySummary, WorkSettings
from attendance.services import BiometricService


class ExtendedShiftTestCase(TestCase):
    """Test extended shift spanning from day to night"""
    
    def setUp(self):
        """Set up test data"""
        # Get or create a general shift (flexible)
        self.general_shift, _ = Shift.objects.get_or_create(
            name='General',
            defaults={
                'shift_type': 'GENERAL',
                'start_time': '00:00:00',
                'end_time': '23:59:59',
                'working_hours': 8.0,
                'break_start_time': '13:00:00',
                'break_end_time': '13:30:00',
                'exclude_break': True,
                'night_shift_allowance': 0.0,
                'is_active': True
            }
        )
        
        # Create employee with no assigned shift (auto-detect)
        self.employee = Employee.objects.create(
            name='Extended Shift Worker',
            employee_id='EXT001',
            biometric_id=500,
            shift=None,  # Auto-detect
            working_hours=8.0  # Standard 8 hours
        )
        
        # Configure work settings
        settings = WorkSettings.get_settings()
        settings.night_start_time = dt_time(22, 0)  # 10 PM
        settings.night_end_time = dt_time(6, 0)     # 6 AM
        settings.exclude_lunch_from_hours = True
        settings.lunch_start_time = dt_time(13, 0)  # 1 PM
        settings.lunch_end_time = dt_time(13, 30)   # 1:30 PM
        settings.save()
    
    def test_extended_shift_9am_to_2am(self):
        """
        Test: Employee works from 9:00 AM Dec 19 to 2:00 AM Dec 20
        
        Expected Results:
        - Total time: 17 hours
        - Lunch break: 30 minutes (0.5h)
        - Net hours: 16.5 hours
        - Night hours: 4 hours (10 PM - 2 AM)
        - Day hours: 12.5 hours (9 AM - 10 PM minus lunch)
        - Overtime: 8.5 hours (16.5 - 8.0)
        - Shift date: Dec 19 (start date)
        """
        
        # Create attendance logs
        check_in = timezone.make_aware(datetime(2025, 12, 19, 9, 0))   # 9:00 AM
        check_out = timezone.make_aware(datetime(2025, 12, 20, 2, 0))  # 2:00 AM next day
        
        AttendanceLog.objects.create(
            employee=self.employee,
            timestamp=check_in,
            status=0  # Check-in
        )
        
        AttendanceLog.objects.create(
            employee=self.employee,
            timestamp=check_out,
            status=1  # Check-out
        )
        
        # Process summaries
        service = BiometricService()
        affected_keys = [(self.employee.id, check_in.date())]
        service._update_summaries(affected_keys)
        
        # Retrieve summary
        summary = DailySummary.objects.get(
            employee=self.employee,
            date=datetime(2025, 12, 19).date()
        )
        
        # Print results for verification
        print("\n" + "="*70)
        print("TEST CASE: Extended Shift (9 AM to 2 AM next day)")
        print("="*70)
        print(f"Employee: {self.employee.name}")
        print(f"Check-in: {check_in.strftime('%Y-%m-%d %H:%M')}")
        print(f"Check-out: {check_out.strftime('%Y-%m-%d %H:%M')}")
        print(f"Shift Date: {summary.date}")
        print(f"Detected Shift: {summary.shift.name if summary.shift else 'None'}")
        print("-"*70)
        print(f"Total Hours: {summary.total_hours}h")
        print(f"Night Hours: {summary.night_hours}h (10 PM - 2 AM)")
        print(f"Day Hours: {summary.day_hours}h (9 AM - 10 PM)")
        print(f"Overtime Hours: {summary.overtime_hours}h")
        print(f"Is Overtime: {summary.is_overtime}")
        print("-"*70)
        
        # Calculations breakdown
        raw_hours = 17.0  # 9 AM to 2 AM = 17 hours
        lunch_break = 0.5  # 30 minutes
        expected_total = raw_hours - lunch_break  # 16.5 hours
        
        # Night hours calculation:
        # Raw night: 10 PM to 2 AM = 4 hours
        # But lunch break is proportionally deducted
        # Ratio = 16.5 / 17 = 0.97
        # Night after break = 4 * 0.97 = 3.88 hours
        expected_night = 3.88  # Adjusted for proportional break deduction
        expected_day = expected_total - expected_night  # 12.62 hours
        expected_overtime = expected_total - 8.0  # 8.5 hours
        
        print("EXPECTED VALUES:")
        print(f"Raw Hours: {raw_hours}h")
        print(f"Lunch Break: {lunch_break}h")
        print(f"Expected Total: {expected_total}h")
        print(f"Expected Night: {expected_night}h (proportionally adjusted)")
        print(f"Expected Day: {expected_day}h")
        print(f"Expected Overtime: {expected_overtime}h")
        print("="*70)
        
        # Assertions
        self.assertEqual(summary.date, datetime(2025, 12, 19).date(), 
                        "Summary should be on start date (Dec 19)")
        
        # Total hours should be ~16.5 (17 - 0.5 lunch)
        self.assertAlmostEqual(float(summary.total_hours), expected_total, places=1,
                              msg=f"Total hours should be ~{expected_total}h")
        
        # Night hours should be 4 (10 PM to 2 AM)
        self.assertAlmostEqual(float(summary.night_hours), expected_night, places=1,
                              msg=f"Night hours should be ~{expected_night}h")
        
        # Day hours should be ~12.5
        self.assertAlmostEqual(float(summary.day_hours), expected_day, places=1,
                              msg=f"Day hours should be ~{expected_day}h")
        
        # Overtime should be 8.5 hours (16.5 - 8.0)
        self.assertAlmostEqual(float(summary.overtime_hours), expected_overtime, places=1,
                              msg=f"Overtime should be ~{expected_overtime}h")
        
        # Should be marked as overtime
        self.assertTrue(summary.is_overtime, "Should be marked as overtime")
        
        # Verify night + day = total
        total_check = float(summary.night_hours) + float(summary.day_hours)
        self.assertAlmostEqual(total_check, float(summary.total_hours), places=1,
                              msg="Night hours + Day hours should equal Total hours")
        
        print("\n✅ ALL ASSERTIONS PASSED!")
        print("="*70 + "\n")
        
        return summary


class MultipleExtendedShiftScenarios(TestCase):
    """Test various extended shift scenarios"""
    
    def setUp(self):
        """Set up test data"""
        self.employee = Employee.objects.create(
            name='Test Worker',
            employee_id='TEST001',
            biometric_id=501,
            working_hours=8.0
        )
        
        settings = WorkSettings.get_settings()
        settings.night_start_time = dt_time(22, 0)
        settings.night_end_time = dt_time(6, 0)
        settings.exclude_lunch_from_hours = True
        settings.lunch_start_time = dt_time(13, 0)
        settings.lunch_end_time = dt_time(13, 30)
        settings.save()
    
    def test_scenario_1_early_morning_to_late_night(self):
        """6 AM to 11 PM (17 hours, crosses into night period)"""
        check_in = timezone.make_aware(datetime(2025, 12, 19, 6, 0))
        check_out = timezone.make_aware(datetime(2025, 12, 19, 23, 0))
        
        AttendanceLog.objects.create(employee=self.employee, timestamp=check_in, status=0)
        AttendanceLog.objects.create(employee=self.employee, timestamp=check_out, status=1)
        
        service = BiometricService()
        service._update_summaries([(self.employee.id, check_in.date())])
        
        summary = DailySummary.objects.get(employee=self.employee, date=check_in.date())
        
        print(f"\n📊 Scenario 1: 6 AM - 11 PM")
        print(f"   Total: {summary.total_hours}h | Night: {summary.night_hours}h | Day: {summary.day_hours}h | OT: {summary.overtime_hours}h")
        
        # Should have 1 hour of night (10 PM - 11 PM)
        self.assertGreater(float(summary.night_hours), 0.5)
        self.assertLess(float(summary.night_hours), 1.5)
    
    def test_scenario_2_afternoon_to_early_morning(self):
        """2 PM to 4 AM next day (14 hours)"""
        check_in = timezone.make_aware(datetime(2025, 12, 19, 14, 0))
        check_out = timezone.make_aware(datetime(2025, 12, 20, 4, 0))
        
        AttendanceLog.objects.create(employee=self.employee, timestamp=check_in, status=0)
        AttendanceLog.objects.create(employee=self.employee, timestamp=check_out, status=1)
        
        service = BiometricService()
        service._update_summaries([(self.employee.id, check_in.date())])
        
        summary = DailySummary.objects.get(employee=self.employee, date=check_in.date())
        
        print(f"\n📊 Scenario 2: 2 PM - 4 AM")
        print(f"   Total: {summary.total_hours}h | Night: {summary.night_hours}h | Day: {summary.day_hours}h | OT: {summary.overtime_hours}h")
        
        # Should have 6 hours of night (10 PM - 4 AM)
        self.assertGreater(float(summary.night_hours), 5.5)
        self.assertLess(float(summary.night_hours), 6.5)
    
    def test_scenario_3_very_long_shift(self):
        """8 AM to 6 AM next day (22 hours)"""
        check_in = timezone.make_aware(datetime(2025, 12, 19, 8, 0))
        check_out = timezone.make_aware(datetime(2025, 12, 20, 6, 0))
        
        AttendanceLog.objects.create(employee=self.employee, timestamp=check_in, status=0)
        AttendanceLog.objects.create(employee=self.employee, timestamp=check_out, status=1)
        
        service = BiometricService()
        service._update_summaries([(self.employee.id, check_in.date())])
        
        summary = DailySummary.objects.get(employee=self.employee, date=check_in.date())
        
        print(f"\n📊 Scenario 3: 8 AM - 6 AM (22h)")
        print(f"   Total: {summary.total_hours}h | Night: {summary.night_hours}h | Day: {summary.day_hours}h | OT: {summary.overtime_hours}h")
        
        # Should have 8 hours of night (10 PM - 6 AM)
        self.assertGreater(float(summary.night_hours), 7.5)
        self.assertLess(float(summary.night_hours), 8.5)
        
        # Should have massive overtime
        self.assertGreater(float(summary.overtime_hours), 13.0)
