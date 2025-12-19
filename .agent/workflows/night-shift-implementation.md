# Night Shift Support - Implementation Plan

## Current Limitations

The application currently:
1. Groups attendance by calendar date only
2. Assumes first check-in and last check-out are on the same day
3. Cannot handle shifts that span midnight (e.g., 10 PM - 6 AM)
4. Lunch break logic assumes daytime hours only

## Proposed Solution

### Phase 1: Database Schema Updates

#### 1.1 Add Shift Model
```python
class Shift(models.Model):
    SHIFT_TYPES = [
        ('DAY', 'Day Shift'),
        ('NIGHT', 'Night Shift'),
        ('GENERAL', 'General/Flexible'),
    ]
    
    name = models.CharField(max_length=50)
    shift_type = models.CharField(max_length=10, choices=SHIFT_TYPES, default='DAY')
    start_time = models.TimeField(help_text="Shift start time")
    end_time = models.TimeField(help_text="Shift end time")
    working_hours = models.DecimalField(max_digits=4, decimal_places=2)
    
    # Break times
    break_start_time = models.TimeField(null=True, blank=True)
    break_end_time = models.TimeField(null=True, blank=True)
    exclude_break = models.BooleanField(default=True)
    
    # Night shift allowance
    night_shift_allowance = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Extra pay percentage for night shift"
    )
    
    is_active = models.BooleanField(default=True)
    
    def is_night_shift(self):
        """Check if shift crosses midnight"""
        return self.end_time < self.start_time
```

#### 1.2 Update Employee Model
```python
class Employee(models.Model):
    # ... existing fields ...
    shift = models.ForeignKey(
        Shift, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Assigned shift (leave blank for flexible)"
    )
```

#### 1.3 Update DailySummary Model
```python
class DailySummary(models.Model):
    # ... existing fields ...
    shift = models.ForeignKey(Shift, on_delete=models.SET_NULL, null=True, blank=True)
    shift_date = models.DateField(help_text="The date this shift belongs to (for night shifts, this is the start date)")
    night_shift_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    night_shift_allowance = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
```

### Phase 2: Shift Detection Logic

#### 2.1 Smart Shift Assignment Algorithm
```python
def detect_shift_for_attendance(employee, check_in_time):
    """
    Detect which shift an attendance record belongs to
    
    Logic:
    1. If employee has assigned shift, use that
    2. Otherwise, find shift based on check-in time
    3. For night shifts, determine the correct shift date
    """
    
    if employee.shift:
        shift = employee.shift
    else:
        # Find shift based on check-in time
        shift = find_matching_shift(check_in_time.time())
    
    # Determine shift date
    if shift and shift.is_night_shift():
        # If checking in after midnight but before shift end, 
        # this belongs to previous day's shift
        if check_in_time.time() < shift.end_time:
            shift_date = check_in_time.date() - timedelta(days=1)
        else:
            shift_date = check_in_time.date()
    else:
        shift_date = check_in_time.date()
    
    return shift, shift_date
```

#### 2.2 Night Shift Hours Calculation
```python
def calculate_night_shift_hours(check_in, check_out, shift):
    """
    Calculate hours worked during night time (e.g., 10 PM - 6 AM)
    
    Returns:
    - total_hours: Total working hours
    - night_hours: Hours worked during night period
    - day_hours: Hours worked during day period
    """
    
    # Define night period (e.g., 10 PM to 6 AM)
    NIGHT_START = time(22, 0)  # 10 PM
    NIGHT_END = time(6, 0)     # 6 AM
    
    # Implementation details...
```

### Phase 3: Updated Summary Calculation

#### 3.1 Modified _update_summaries Method
```python
def _update_summaries(self, affected_keys):
    """
    Updated to handle night shifts:
    1. Group logs by shift_date instead of calendar date
    2. Calculate night shift hours separately
    3. Apply night shift allowance
    4. Handle break times based on shift
    """
    
    for emp_id, log_date in affected_keys:
        # Get all logs for this employee around this date
        # (include previous and next day for night shift detection)
        start_date = log_date - timedelta(days=1)
        end_date = log_date + timedelta(days=1)
        
        logs = AttendanceLog.objects.filter(
            employee_id=emp_id,
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date
        ).order_by('timestamp')
        
        # Group logs by detected shift
        shift_groups = group_logs_by_shift(logs)
        
        # Process each shift group
        for shift_date, shift_logs in shift_groups.items():
            # Calculate hours with night shift logic
            # ...
```

### Phase 4: UI Updates

#### 4.1 Shift Management Page
- Create/Edit/Delete shifts
- Assign shifts to employees
- View shift schedules

#### 4.2 Updated Reports
- Show shift information in daily summaries
- Display night shift hours separately
- Calculate night shift allowance in monthly reports

#### 4.3 Settings Page Enhancement
- Add shift configuration section
- Configure night shift premium rates
- Set night period definition (e.g., 10 PM - 6 AM)

### Phase 5: Migration Strategy

#### 5.1 Create Default Shifts
```python
# Migration to create default shifts
def create_default_shifts(apps, schema_editor):
    Shift = apps.get_model('attendance', 'Shift')
    
    # Day Shift
    Shift.objects.create(
        name='Day Shift',
        shift_type='DAY',
        start_time='09:00:00',
        end_time='18:00:00',
        working_hours=8.0,
        break_start_time='13:00:00',
        break_end_time='13:30:00',
        exclude_break=True
    )
    
    # Night Shift
    Shift.objects.create(
        name='Night Shift',
        shift_type='NIGHT',
        start_time='22:00:00',
        end_time='06:00:00',
        working_hours=8.0,
        break_start_time='02:00:00',
        break_end_time='02:30:00',
        exclude_break=True,
        night_shift_allowance=20.0  # 20% extra
    )
    
    # General Shift (flexible)
    Shift.objects.create(
        name='General/Flexible',
        shift_type='GENERAL',
        start_time='00:00:00',
        end_time='23:59:59',
        working_hours=8.0,
        exclude_break=False
    )
```

## Implementation Steps

### Step 1: Database Changes (2-3 hours)
1. Create Shift model
2. Update Employee model
3. Update DailySummary model
4. Create and run migrations
5. Create default shifts

### Step 2: Core Logic Updates (4-5 hours)
1. Implement shift detection algorithm
2. Update _update_summaries for night shifts
3. Add night hours calculation
4. Update break time logic per shift

### Step 3: API/Views Updates (2-3 hours)
1. Create shift management views
2. Update employee views for shift assignment
3. Update report views to show shift data

### Step 4: UI Development (3-4 hours)
1. Create shift management page
2. Update employee settings to show shift
3. Update daily/monthly reports to display shift info
4. Add night shift indicators

### Step 5: Testing & Validation (2-3 hours)
1. Test day shift calculations
2. Test night shift spanning midnight
3. Test shift transitions
4. Validate overtime calculations
5. Test edge cases (late check-in, early check-out)

## Total Estimated Time: 13-18 hours

## Key Features After Implementation

✅ Support for multiple shift types (Day, Night, General)
✅ Automatic detection of shift based on check-in time
✅ Proper handling of shifts spanning midnight
✅ Separate tracking of night shift hours
✅ Night shift allowance/premium calculation
✅ Shift-specific break times
✅ Flexible shift assignment per employee
✅ Accurate overtime calculation per shift
✅ Enhanced reporting with shift information

## Example Scenarios

### Scenario 1: Night Shift Worker
- Employee: John (Night Shift: 10 PM - 6 AM)
- Check-in: Dec 19, 10:15 PM
- Check-out: Dec 20, 6:10 AM
- **Shift Date**: Dec 19 (shift belongs to the day it started)
- **Total Hours**: 7.92h (minus 30min break)
- **Night Hours**: 7.92h (all hours are night hours)
- **Allowance**: 20% extra pay

### Scenario 2: Day Shift Worker
- Employee: Sarah (Day Shift: 9 AM - 6 PM)
- Check-in: Dec 19, 9:00 AM
- Check-out: Dec 19, 6:00 PM
- **Shift Date**: Dec 19
- **Total Hours**: 8.5h (minus 30min lunch)
- **Night Hours**: 0h
- **Overtime**: 0.5h

### Scenario 3: Flexible Worker
- Employee: Mike (No assigned shift)
- Check-in: Dec 19, 2:00 PM
- Check-out: Dec 19, 11:00 PM
- **Detected Shift**: Day Shift (based on check-in time)
- **Total Hours**: 9h
- **Overtime**: 1h

## Backward Compatibility

- Existing employees without shift assignment will use "General" shift
- Existing summaries remain valid
- New calculations only apply to new attendance records
- Option to recalculate historical data with shift logic
