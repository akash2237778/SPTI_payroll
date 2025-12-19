"""
Unit tests for night shift functionality
"""
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, time as dt_time, timedelta
from attendance.models import Shift, Employee, AttendanceLog, DailySummary, WorkSettings
from attendance.shift_utils import (
    detect_shift_for_attendance,
    find_matching_shift,
    is_time_in_shift_range,
    calculate_night_hours,
    calculate_break_overlap
)


class ShiftModelTest(TestCase):
    """Test Shift model functionality"""
    
    def setUp(self):
        """Create test shifts"""
        self.day_shift = Shift.objects.create(
            name='Day Shift Test',
            shift_type='DAY',
            start_time='09:00:00',
            end_time='18:00:00',
            working_hours=8.0,
            break_start_time='13:00:00',
            break_end_time='13:30:00',
            exclude_break=True,
            night_shift_allowance=0.0,
            is_active=True
        )
        
        self.night_shift = Shift.objects.create(
            name='Night Shift Test',
            shift_type='NIGHT',
            start_time='22:00:00',
            end_time='06:00:00',
            working_hours=8.0,
            break_start_time='02:00:00',
            break_end_time='02:30:00',
            exclude_break=True,
            night_shift_allowance=20.0,
            is_active=True
        )
    
    def test_is_night_shift(self):
        """Test night shift detection"""
        self.assertFalse(self.day_shift.is_night_shift())
        self.assertTrue(self.night_shift.is_night_shift())
    
    def test_break_duration_calculation(self):
        """Test break duration calculation"""
        day_break = self.day_shift.get_break_duration_hours()
        self.assertEqual(day_break, 0.5)  # 30 minutes
        
        night_break = self.night_shift.get_break_duration_hours()
        self.assertEqual(night_break, 0.5)


class ShiftDetectionTest(TestCase):
    """Test shift detection logic"""
    
    def setUp(self):
        """Create test data"""
        self.day_shift = Shift.objects.create(
            name='Day Shift',
            shift_type='DAY',
            start_time='09:00:00',
            end_time='18:00:00',
            working_hours=8.0,
            is_active=True
        )
        
        self.night_shift = Shift.objects.create(
            name='Night Shift',
            shift_type='NIGHT',
            start_time='22:00:00',
            end_time='06:00:00',
            working_hours=8.0,
            is_active=True
        )
        
        self.employee_day = Employee.objects.create(
            name='Day Worker',
            employee_id='DAY001',
            biometric_id=1,
            shift=self.day_shift
        )
        
        self.employee_night = Employee.objects.create(
            name='Night Worker',
            employee_id='NIGHT001',
            biometric_id=2,
            shift=self.night_shift
        )
        
        self.employee_flexible = Employee.objects.create(
            name='Flexible Worker',
            employee_id='FLEX001',
            biometric_id=3,
            shift=None
        )
    
    def test_assigned_shift_detection(self):
        """Test detection for employees with assigned shifts"""
        # Day shift check-in
        check_in = timezone.make_aware(datetime(2025, 12, 19, 9, 0))
        shift, shift_date = detect_shift_for_attendance(self.employee_day, check_in)
        
        self.assertEqual(shift, self.day_shift)
        self.assertEqual(shift_date, check_in.date())
    
    def test_night_shift_date_assignment(self):
        """Test that night shift gets correct date"""
        # Night shift check-in at 10 PM
        check_in = timezone.make_aware(datetime(2025, 12, 19, 22, 0))
        shift, shift_date = detect_shift_for_attendance(self.employee_night, check_in)
        
        self.assertEqual(shift, self.night_shift)
        self.assertEqual(shift_date, datetime(2025, 12, 19).date())
        
        # Check-in after midnight (still belongs to previous day's shift)
        check_in_midnight = timezone.make_aware(datetime(2025, 12, 20, 2, 0))
        shift, shift_date = detect_shift_for_attendance(self.employee_night, check_in_midnight)
        
        self.assertEqual(shift, self.night_shift)
        self.assertEqual(shift_date, datetime(2025, 12, 19).date())
    
    def test_auto_detect_day_shift(self):
        """Test auto-detection for day shift"""
        check_in = timezone.make_aware(datetime(2025, 12, 19, 10, 0))
        shift, shift_date = detect_shift_for_attendance(self.employee_flexible, check_in)
        
        self.assertIsNotNone(shift)
        self.assertEqual(shift.shift_type, 'DAY')
    
    def test_auto_detect_night_shift(self):
        """Test auto-detection for night shift"""
        check_in = timezone.make_aware(datetime(2025, 12, 19, 23, 0))
        shift, shift_date = detect_shift_for_attendance(self.employee_flexible, check_in)
        
        self.assertIsNotNone(shift)
        self.assertEqual(shift.shift_type, 'NIGHT')
    
    def test_time_in_shift_range(self):
        """Test time range checking"""
        # Day shift
        self.assertTrue(is_time_in_shift_range(
            dt_time(9, 0),
            dt_time(9, 0),
            dt_time(18, 0)
        ))
        
        self.assertTrue(is_time_in_shift_range(
            dt_time(12, 0),
            dt_time(9, 0),
            dt_time(18, 0)
        ))
        
        # Night shift (crosses midnight)
        self.assertTrue(is_time_in_shift_range(
            dt_time(23, 0),
            dt_time(22, 0),
            dt_time(6, 0)
        ))
        
        self.assertTrue(is_time_in_shift_range(
            dt_time(2, 0),
            dt_time(22, 0),
            dt_time(6, 0)
        ))


class NightHoursCalculationTest(TestCase):
    """Test night hours calculation"""
    
    def setUp(self):
        """Set up work settings"""
        self.settings = WorkSettings.get_settings()
        self.settings.night_start_time = dt_time(22, 0)
        self.settings.night_end_time = dt_time(6, 0)
        self.settings.save()
    
    def test_all_day_hours(self):
        """Test work entirely during day"""
        check_in = timezone.make_aware(datetime(2025, 12, 19, 9, 0))
        check_out = timezone.make_aware(datetime(2025, 12, 19, 17, 0))
        
        night_hours, day_hours = calculate_night_hours(
            check_in,
            check_out,
            self.settings.night_start_time,
            self.settings.night_end_time
        )
        
        self.assertEqual(night_hours, 0.0)
        self.assertEqual(day_hours, 8.0)
    
    def test_all_night_hours(self):
        """Test work entirely during night"""
        check_in = timezone.make_aware(datetime(2025, 12, 19, 22, 0))
        check_out = timezone.make_aware(datetime(2025, 12, 20, 6, 0))
        
        night_hours, day_hours = calculate_night_hours(
            check_in,
            check_out,
            self.settings.night_start_time,
            self.settings.night_end_time
        )
        
        self.assertEqual(night_hours, 8.0)
        self.assertEqual(day_hours, 0.0)
    
    def test_mixed_hours(self):
        """Test work spanning day and night"""
        # Work from 8 PM to 8 AM (12 hours total)
        check_in = timezone.make_aware(datetime(2025, 12, 19, 20, 0))
        check_out = timezone.make_aware(datetime(2025, 12, 20, 8, 0))
        
        night_hours, day_hours = calculate_night_hours(
            check_in,
            check_out,
            self.settings.night_start_time,
            self.settings.night_end_time
        )
        
        # Night: 10 PM - 6 AM = 8 hours
        # Day: 8 PM - 10 PM + 6 AM - 8 AM = 4 hours
        self.assertEqual(night_hours, 8.0)
        self.assertEqual(day_hours, 4.0)
    
    def test_partial_night_hours(self):
        """Test work partially in night period"""
        # Work from 11 PM to 2 AM (3 hours, all night)
        check_in = timezone.make_aware(datetime(2025, 12, 19, 23, 0))
        check_out = timezone.make_aware(datetime(2025, 12, 20, 2, 0))
        
        night_hours, day_hours = calculate_night_hours(
            check_in,
            check_out,
            self.settings.night_start_time,
            self.settings.night_end_time
        )
        
        self.assertEqual(night_hours, 3.0)
        self.assertEqual(day_hours, 0.0)


class BreakCalculationTest(TestCase):
    """Test break overlap calculation"""
    
    def test_break_fully_within_work(self):
        """Test break entirely within work period"""
        work_start = timezone.make_aware(datetime(2025, 12, 19, 9, 0))
        work_end = timezone.make_aware(datetime(2025, 12, 19, 18, 0))
        break_start = dt_time(13, 0)
        break_end = dt_time(13, 30)
        
        break_hours = calculate_break_overlap(
            work_start,
            work_end,
            break_start,
            break_end
        )
        
        self.assertEqual(break_hours, 0.5)
    
    def test_no_break_overlap(self):
        """Test no overlap between work and break"""
        work_start = timezone.make_aware(datetime(2025, 12, 19, 9, 0))
        work_end = timezone.make_aware(datetime(2025, 12, 19, 12, 0))
        break_start = dt_time(13, 0)
        break_end = dt_time(13, 30)
        
        break_hours = calculate_break_overlap(
            work_start,
            work_end,
            break_start,
            break_end
        )
        
        self.assertEqual(break_hours, 0.0)
    
    def test_partial_break_overlap(self):
        """Test partial overlap"""
        work_start = timezone.make_aware(datetime(2025, 12, 19, 13, 15))
        work_end = timezone.make_aware(datetime(2025, 12, 19, 18, 0))
        break_start = dt_time(13, 0)
        break_end = dt_time(13, 30)
        
        break_hours = calculate_break_overlap(
            work_start,
            work_end,
            break_start,
            break_end
        )
        
        # Only 15 minutes overlap (13:15 - 13:30)
        self.assertEqual(break_hours, 0.25)
    
    def test_night_shift_break(self):
        """Test break during night shift"""
        work_start = timezone.make_aware(datetime(2025, 12, 19, 22, 0))
        work_end = timezone.make_aware(datetime(2025, 12, 20, 6, 0))
        break_start = dt_time(2, 0)
        break_end = dt_time(2, 30)
        
        break_hours = calculate_break_overlap(
            work_start,
            work_end,
            break_start,
            break_end
        )
        
        self.assertEqual(break_hours, 0.5)


class IntegrationTest(TestCase):
    """End-to-end integration tests"""
    
    def setUp(self):
        """Create complete test scenario"""
        # Create shifts
        self.night_shift = Shift.objects.create(
            name='Night Shift',
            shift_type='NIGHT',
            start_time='22:00:00',
            end_time='06:00:00',
            working_hours=8.0,
            break_start_time='02:00:00',
            break_end_time='02:30:00',
            exclude_break=True,
            night_shift_allowance=20.0,
            is_active=True
        )
        
        # Create employee
        self.employee = Employee.objects.create(
            name='Test Worker',
            employee_id='TEST001',
            biometric_id=999,
            shift=self.night_shift
        )
        
        # Set up work settings
        settings = WorkSettings.get_settings()
        settings.night_start_time = dt_time(22, 0)
        settings.night_end_time = dt_time(6, 0)
        settings.save()
    
    def test_complete_night_shift_workflow(self):
        """Test complete night shift from attendance to summary"""
        from attendance.services import BiometricService
        
        # Create attendance logs
        check_in = timezone.make_aware(datetime(2025, 12, 19, 22, 15))
        check_out = timezone.make_aware(datetime(2025, 12, 20, 6, 10))
        
        AttendanceLog.objects.create(
            employee=self.employee,
            timestamp=check_in,
            status=0
        )
        
        AttendanceLog.objects.create(
            employee=self.employee,
            timestamp=check_out,
            status=1
        )
        
        # Trigger summary update
        service = BiometricService()
        affected_keys = [(self.employee.id, check_in.date())]
        service._update_summaries(affected_keys)
        
        # Verify summary
        summary = DailySummary.objects.get(
            employee=self.employee,
            date=datetime(2025, 12, 19).date()
        )
        
        # Check shift assignment
        self.assertEqual(summary.shift, self.night_shift)
        
        # Check hours (8h - 0.5h break = 7.5h, but actual time is 7.92h - 0.5h = 7.42h)
        self.assertGreater(summary.total_hours, 7.0)
        self.assertLess(summary.total_hours, 8.0)
        
        # Check night hours (should be all hours since it's night shift)
        self.assertGreater(summary.night_hours, 7.0)
        
        # Check overtime (7.42h < 8h, so no OT)
        self.assertEqual(summary.overtime_hours, 0.0)
        
        # Check night allowance
        self.assertGreater(summary.night_shift_allowance_amount, 0.0)
        
        print(f"\n✅ Integration Test Results:")
        print(f"   Shift: {summary.shift.name}")
        print(f"   Total Hours: {summary.total_hours}h")
        print(f"   Night Hours: {summary.night_hours}h")
        print(f"   Day Hours: {summary.day_hours}h")
        print(f"   Overtime: {summary.overtime_hours}h")
        print(f"   Night Allowance: {summary.night_shift_allowance_amount}h")


class EdgeCaseTest(TestCase):
    """Test edge cases and boundary conditions"""
    
    def test_exactly_midnight_checkin(self):
        """Test check-in exactly at midnight"""
        night_shift = Shift.objects.create(
            name='Night Shift',
            shift_type='NIGHT',
            start_time='22:00:00',
            end_time='06:00:00',
            working_hours=8.0,
            is_active=True
        )
        
        employee = Employee.objects.create(
            name='Midnight Worker',
            employee_id='MID001',
            biometric_id=100,
            shift=night_shift
        )
        
        check_in = timezone.make_aware(datetime(2025, 12, 20, 0, 0))
        shift, shift_date = detect_shift_for_attendance(employee, check_in)
        
        # Should belong to Dec 19's night shift
        self.assertEqual(shift_date, datetime(2025, 12, 19).date())
    
    def test_very_short_work_period(self):
        """Test very short work period"""
        check_in = timezone.make_aware(datetime(2025, 12, 19, 9, 0))
        check_out = timezone.make_aware(datetime(2025, 12, 19, 9, 15))
        
        night_hours, day_hours = calculate_night_hours(
            check_in,
            check_out,
            dt_time(22, 0),
            dt_time(6, 0)
        )
        
        self.assertEqual(night_hours, 0.0)
        self.assertEqual(day_hours, 0.25)
    
    def test_multi_day_work(self):
        """Test work spanning multiple days"""
        # Work from 6 AM Day 1 to 6 AM Day 2 (24 hours)
        check_in = timezone.make_aware(datetime(2025, 12, 19, 6, 0))
        check_out = timezone.make_aware(datetime(2025, 12, 20, 6, 0))
        
        night_hours, day_hours = calculate_night_hours(
            check_in,
            check_out,
            dt_time(22, 0),
            dt_time(6, 0)
        )
        
        # Night: 10 PM - 6 AM = 8 hours
        # Day: 6 AM - 10 PM = 16 hours
        self.assertEqual(night_hours, 8.0)
        self.assertEqual(day_hours, 16.0)
