from django.db import models
from datetime import time as dt_time

class Shift(models.Model):
    """
    Shift configuration for different work schedules
    """
    SHIFT_TYPES = [
        ('DAY', 'Day Shift'),
        ('NIGHT', 'Night Shift'),
        ('GENERAL', 'General/Flexible'),
    ]
    
    name = models.CharField(max_length=50, unique=True)
    shift_type = models.CharField(max_length=10, choices=SHIFT_TYPES, default='DAY')
    start_time = models.TimeField(help_text="Shift start time (HH:MM)")
    end_time = models.TimeField(help_text="Shift end time (HH:MM)")
    working_hours = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        help_text="Expected working hours for this shift"
    )
    
    # Break times
    break_start_time = models.TimeField(
        null=True, 
        blank=True,
        help_text="Break start time (leave blank for no break)"
    )
    break_end_time = models.TimeField(
        null=True, 
        blank=True,
        help_text="Break end time"
    )
    exclude_break = models.BooleanField(
        default=True,
        help_text="Exclude break time from working hours calculation"
    )
    
    # Night shift allowance
    night_shift_allowance = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Extra pay percentage for night shift (e.g., 20.00 for 20%)"
    )
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Shift"
        verbose_name_plural = "Shifts"
    
    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"
    
    def is_night_shift(self):
        """Check if shift crosses midnight"""
        return self.end_time < self.start_time
    
    def get_break_duration_hours(self):
        """Calculate break duration in hours"""
        if not self.break_start_time or not self.break_end_time:
            return 0.0
        
        from datetime import datetime, timedelta, time as dt_time
        
        # Handle both time objects and strings
        if isinstance(self.break_start_time, str):
            break_start = datetime.strptime(self.break_start_time, '%H:%M:%S').time()
        else:
            break_start = self.break_start_time
        
        if isinstance(self.break_end_time, str):
            break_end = datetime.strptime(self.break_end_time, '%H:%M:%S').time()
        else:
            break_end = self.break_end_time
        
        start = datetime.combine(datetime.today(), break_start)
        end = datetime.combine(datetime.today(), break_end)
        
        if end < start:  # Break crosses midnight
            end += timedelta(days=1)
        
        duration = (end - start).total_seconds() / 3600.0
        return duration

class WorkSettings(models.Model):
    """
    Global work settings for the company (singleton model)
    """
    default_working_hours = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        default=8.0,
        help_text="Default working hours per day"
    )
    lunch_start_time = models.TimeField(
        default='13:00:00',
        help_text="Lunch break start time (HH:MM:SS)"
    )
    lunch_end_time = models.TimeField(
        default='13:30:00',
        help_text="Lunch break end time (HH:MM:SS)"
    )
    exclude_lunch_from_hours = models.BooleanField(
        default=True,
        help_text="Exclude lunch break from total working hours calculation"
    )
    
    # Night shift settings
    night_start_time = models.TimeField(
        default='22:00:00',
        help_text="Night period start time (for night hours calculation)"
    )
    night_end_time = models.TimeField(
        default='06:00:00',
        help_text="Night period end time"
    )
    
    class Meta:
        verbose_name = "Work Settings"
        verbose_name_plural = "Work Settings"
    
    def __str__(self):
        return f"Work Settings (Default: {self.default_working_hours}h, Lunch: {self.lunch_start_time}-{self.lunch_end_time})"
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists (singleton)
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class DeviceSettings(models.Model):
    """
    Biometric device connection settings (singleton model)
    """
    device_ip = models.CharField(
        max_length=15,
        default='192.168.2.66',
        help_text="IP address of the ZK biometric device"
    )
    device_port = models.IntegerField(
        default=4370,
        help_text="Port number for device connection"
    )
    timeout = models.IntegerField(
        default=60,
        help_text="Connection timeout in seconds"
    )
    password = models.IntegerField(
        default=0,
        help_text="Device password (usually 0)"
    )
    force_udp = models.BooleanField(
        default=True,
        help_text="Force UDP connection"
    )
    ommit_ping = models.BooleanField(
        default=True,
        help_text="Skip initial ping check"
    )
    
    class Meta:
        verbose_name = "Device Settings"
        verbose_name_plural = "Device Settings"
    
    def __str__(self):
        return f"Device Settings ({self.device_ip}:{self.device_port})"
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists (singleton)
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance"""
        from django.conf import settings as django_settings
        obj, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'device_ip': django_settings.ZK_DEVICE_IP,
            }
        )
        return obj

class Employee(models.Model):
    name = models.CharField(max_length=100)
    employee_id = models.CharField(max_length=50, unique=True, help_text="Internal Company ID")
    biometric_id = models.IntegerField(unique=True, help_text="ID on the ZK Device")
    working_hours = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        default=8.0,
        null=True, 
        blank=True,
        help_text="Custom working hours for this employee (defaults to 8.0 hours)"
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        help_text="Assigned shift (leave blank for auto-detection)"
    )

    def __str__(self):
        return f"{self.name} ({self.employee_id})"
    
    def get_working_hours(self):
        """Get working hours for this employee (custom > shift > default)"""
        if self.working_hours:
            return float(self.working_hours)
        if self.shift:
            return float(self.shift.working_hours)
        return float(WorkSettings.get_settings().default_working_hours)
    
    def get_shift(self):
        """Get assigned shift or None"""
        return self.shift

class AttendanceLog(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField()
    status = models.IntegerField(default=0, help_text="Device Status Code (0=Check-In, 1=Check-Out, etc.)")
    verification_mode = models.IntegerField(default=1, help_text="Verification Mode")

    class Meta:
        unique_together = ('employee', 'timestamp')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.employee.name} - {self.timestamp}"

class DailySummary(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='summaries')
    date = models.DateField(help_text="Calendar date (for day shifts) or shift start date (for night shifts)")
    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The shift this summary belongs to"
    )
    first_check_in = models.TimeField(null=True, blank=True)
    last_check_out = models.TimeField(null=True, blank=True)
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    
    # Night shift tracking
    night_hours = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Hours worked during night period"
    )
    day_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Hours worked during day period"
    )
    
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0.0, help_text="Overtime hours for this day")
    is_overtime = models.BooleanField(default=False)
    
    # Night shift allowance
    night_shift_allowance_amount = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.0,
        help_text="Calculated night shift allowance amount"
    )
    
    class Meta:
        unique_together = ('employee', 'date', 'shift')
        ordering = ['-date']

    def __str__(self):
        shift_info = f" ({self.shift.name})" if self.shift else ""
        return f"{self.employee.name} - {self.date}{shift_info}"

