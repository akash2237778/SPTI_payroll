"""
Shift detection and calculation utilities for attendance system
"""
from datetime import datetime, timedelta, time as dt_time
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def detect_shift_for_attendance(employee, check_in_time):
    """
    Detect which shift an attendance record belongs to
    
    Args:
        employee: Employee instance
        check_in_time: datetime of check-in
    
    Returns:
        tuple: (Shift instance or None, shift_date)
    """
    from .models import Shift
    
    # If employee has assigned shift, use that
    if employee.shift:
        shift = employee.shift
    else:
        # Find shift based on check-in time
        shift = find_matching_shift(check_in_time.time())
    
    # Determine shift date
    if shift and shift.is_night_shift():
        # For night shifts crossing midnight
        # If checking in after midnight but before shift end, 
        # this belongs to previous day's shift
        if check_in_time.time() < shift.end_time:
            shift_date = check_in_time.date() - timedelta(days=1)
        else:
            shift_date = check_in_time.date()
    else:
        shift_date = check_in_time.date()
    
    return shift, shift_date


def find_matching_shift(check_in_time):
    """
    Find the best matching shift for a given check-in time
    
    Args:
        check_in_time: time object
    
    Returns:
        Shift instance or None
    """
    from .models import Shift
    
    active_shifts = Shift.objects.filter(is_active=True).exclude(shift_type='GENERAL')
    
    for shift in active_shifts:
        if is_time_in_shift_range(check_in_time, shift.start_time, shift.end_time):
            return shift
    
    # If no match, return General shift or None
    try:
        return Shift.objects.get(shift_type='GENERAL', is_active=True)
    except Shift.DoesNotExist:
        return None


def is_time_in_shift_range(check_time, shift_start, shift_end):
    """
    Check if a time falls within a shift's time range
    Handles shifts that cross midnight
    
    Args:
        check_time: time object to check
        shift_start: shift start time
        shift_end: shift end time
    
    Returns:
        bool
    """
    # Allow 2 hours before shift start for early check-ins
    tolerance = timedelta(hours=2)
    
    # Convert to datetime for easier comparison
    today = datetime.today().date()
    check_dt = datetime.combine(today, check_time)
    start_dt = datetime.combine(today, shift_start) - tolerance
    
    if shift_end < shift_start:  # Night shift crossing midnight
        end_dt = datetime.combine(today + timedelta(days=1), shift_end)
    else:
        end_dt = datetime.combine(today, shift_end)
    
    return start_dt <= check_dt <= end_dt


def calculate_night_hours(check_in, check_out, night_start_time, night_end_time):
    """
    Calculate hours worked during night period and day period
    
    Args:
        check_in: datetime of check-in
        check_out: datetime of check-out
        night_start_time: time when night period starts (e.g., 22:00)
        night_end_time: time when night period ends (e.g., 06:00)
    
    Returns:
        tuple: (night_hours, day_hours)
    """
    if check_out <= check_in:
        return 0.0, 0.0
    
    # Convert string times to time objects if needed
    if isinstance(night_start_time, str):
        night_start_time = datetime.strptime(night_start_time, '%H:%M:%S').time()
    if isinstance(night_end_time, str):
        night_end_time = datetime.strptime(night_end_time, '%H:%M:%S').time()
    
    # Convert night times to datetime for the relevant dates
    check_in_date = check_in.date()
    check_out_date = check_out.date()
    
    # Build night period ranges
    night_periods = []
    
    # Night period on check-in date
    night_start_dt = datetime.combine(check_in_date, night_start_time)
    if timezone.is_aware(check_in):
        night_start_dt = timezone.make_aware(night_start_dt, timezone.get_current_timezone())
    
    # Night end could be next day if it's before night start (crosses midnight)
    if night_end_time < night_start_time:
        night_end_dt = datetime.combine(check_in_date + timedelta(days=1), night_end_time)
    else:
        night_end_dt = datetime.combine(check_in_date, night_end_time)
    
    if timezone.is_aware(check_in):
        night_end_dt = timezone.make_aware(night_end_dt, timezone.get_current_timezone())
    
    night_periods.append((night_start_dt, night_end_dt))
    
    # If work spans multiple days, add night period for next day
    if check_out_date > check_in_date:
        for day_offset in range(1, (check_out_date - check_in_date).days + 1):
            current_date = check_in_date + timedelta(days=day_offset)
            night_start_dt = datetime.combine(current_date, night_start_time)
            
            if night_end_time < night_start_time:
                night_end_dt = datetime.combine(current_date + timedelta(days=1), night_end_time)
            else:
                night_end_dt = datetime.combine(current_date, night_end_time)
            
            if timezone.is_aware(check_in):
                night_start_dt = timezone.make_aware(night_start_dt, timezone.get_current_timezone())
                night_end_dt = timezone.make_aware(night_end_dt, timezone.get_current_timezone())
            
            night_periods.append((night_start_dt, night_end_dt))
    
    # Calculate overlap between work period and night periods
    total_night_seconds = 0
    
    for night_start, night_end in night_periods:
        # Find overlap
        overlap_start = max(check_in, night_start)
        overlap_end = min(check_out, night_end)
        
        if overlap_start < overlap_end:
            overlap_seconds = (overlap_end - overlap_start).total_seconds()
            total_night_seconds += overlap_seconds
    
    # Calculate total work seconds
    total_work_seconds = (check_out - check_in).total_seconds()
    
    # Convert to hours
    night_hours = total_night_seconds / 3600.0
    total_hours = total_work_seconds / 3600.0
    day_hours = total_hours - night_hours
    
    return round(night_hours, 2), round(day_hours, 2)


def calculate_break_overlap(work_start, work_end, break_start_time, break_end_time):
    """
    Calculate the overlap between work period and break period
    
    Args:
        work_start: datetime of work start
        work_end: datetime of work end
        break_start_time: time object for break start
        break_end_time: time object for break end
    
    Returns:
        float: hours of break overlap
    """
    if not break_start_time or not break_end_time:
        return 0.0
    
    work_date = work_start.date()
    
    # Convert break times to datetime
    break_start_dt = datetime.combine(work_date, break_start_time)
    break_end_dt = datetime.combine(work_date, break_end_time)
    
    # Handle break crossing midnight
    if break_end_time < break_start_time:
        break_end_dt += timedelta(days=1)
    
    # Make timezone aware if needed
    if timezone.is_aware(work_start):
        break_start_dt = timezone.make_aware(break_start_dt, timezone.get_current_timezone())
        break_end_dt = timezone.make_aware(break_end_dt, timezone.get_current_timezone())
    
    # If work spans multiple days, check break on each day
    work_end_date = work_end.date()
    total_break_seconds = 0
    
    current_date = work_date
    while current_date <= work_end_date:
        day_break_start = datetime.combine(current_date, break_start_time)
        day_break_end = datetime.combine(current_date, break_end_time)
        
        if break_end_time < break_start_time:
            day_break_end += timedelta(days=1)
        
        if timezone.is_aware(work_start):
            day_break_start = timezone.make_aware(day_break_start, timezone.get_current_timezone())
            day_break_end = timezone.make_aware(day_break_end, timezone.get_current_timezone())
        
        # Calculate overlap
        overlap_start = max(work_start, day_break_start)
        overlap_end = min(work_end, day_break_end)
        
        if overlap_start < overlap_end:
            total_break_seconds += (overlap_end - overlap_start).total_seconds()
        
        current_date += timedelta(days=1)
    
    return round(total_break_seconds / 3600.0, 2)
