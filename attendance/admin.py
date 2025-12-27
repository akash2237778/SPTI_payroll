from django.contrib import admin
from .models import Shift, Employee, AttendanceLog, DailySummary, WorkSettings, DeviceSettings


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('name', 'shift_type', 'start_time', 'end_time', 'working_hours', 'night_shift_allowance', 'is_active')
    list_filter = ('shift_type', 'is_active')
    search_fields = ('name',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'shift_type', 'is_active')
        }),
        ('Shift Times', {
            'fields': ('start_time', 'end_time', 'working_hours')
        }),
        ('Break Configuration', {
            'fields': ('break_start_time', 'break_end_time', 'exclude_break')
        }),
        ('Night Shift Settings', {
            'fields': ('night_shift_allowance',)
        }),
    )


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'employee_id', 'biometric_id', 'shift', 'working_hours')
    list_filter = ('shift',)
    search_fields = ('name', 'employee_id')
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'employee_id', 'biometric_id')
        }),
        ('Work Configuration', {
            'fields': ('shift', 'working_hours')
        }),
    )


@admin.register(AttendanceLog)
class AttendanceLogAdmin(admin.ModelAdmin):
    list_display = ('employee', 'timestamp', 'status', 'verification_mode', 'is_manually_edited', 'edited_by', 'edited_at')
    list_filter = ('status', 'is_manually_edited', 'timestamp')
    search_fields = ('employee__name', 'employee__employee_id')
    date_hierarchy = 'timestamp'
    readonly_fields = ('edited_at', 'edited_by')
    
    fieldsets = (
        ('Attendance Information', {
            'fields': ('employee', 'timestamp', 'status', 'verification_mode')
        }),
        ('Edit Tracking', {
            'fields': ('is_manually_edited', 'edited_at', 'edited_by'),
            'description': 'Mark as manually edited to prevent sync from overriding this log'
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Automatically mark log as edited and track who edited it"""
        if change:  # Only for updates, not new records
            from django.utils import timezone
            obj.is_manually_edited = True
            obj.edited_at = timezone.now()
            obj.edited_by = request.user.username
        super().save_model(request, obj, form, change)


@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'shift', 'total_hours', 'night_hours', 'day_hours', 'overtime_hours', 'is_overtime')
    list_filter = ('is_overtime', 'shift', 'date')
    search_fields = ('employee__name', 'employee__employee_id')
    date_hierarchy = 'date'
    readonly_fields = ('employee', 'date', 'shift', 'first_check_in', 'last_check_out', 
                       'total_hours', 'night_hours', 'day_hours', 'overtime_hours', 
                       'is_overtime', 'night_shift_allowance_amount')


@admin.register(WorkSettings)
class WorkSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Default Working Hours', {
            'fields': ('default_working_hours',)
        }),
        ('Lunch Break', {
            'fields': ('lunch_start_time', 'lunch_end_time', 'exclude_lunch_from_hours')
        }),
        ('Night Period Definition', {
            'fields': ('night_start_time', 'night_end_time'),
            'description': 'Define when night hours are calculated (e.g., 10 PM to 6 AM)'
        }),
    )
    
    def has_add_permission(self, request):
        # Only allow one WorkSettings instance
        return not WorkSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of WorkSettings
        return False


@admin.register(DeviceSettings)
class DeviceSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Connection Settings', {
            'fields': ('device_ip', 'device_port', 'timeout'),
            'description': 'Configure the biometric device connection parameters'
        }),
        ('Advanced Settings', {
            'fields': ('password', 'force_udp', 'ommit_ping'),
            'classes': ('collapse',),
            'description': 'Advanced connection options (modify only if needed)'
        }),
    )
    
    def has_add_permission(self, request):
        # Only allow one DeviceSettings instance
        return not DeviceSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of DeviceSettings
        return False

