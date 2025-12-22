from django.contrib import admin
from django.urls import path
from attendance.views import (
    trigger_sync_view, index, monthly_report, employee_daily_report,
    settings_view, update_employee_hours, shifts_view, delete_shift, assign_shift
)
from attendance.attendance_log_views import (
    manage_attendance_logs, add_attendance_log, edit_attendance_log,
    delete_attendance_log, bulk_delete_logs
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='dashboard'),
    path('sync-logs/', trigger_sync_view, name='sync_logs'),
    path('monthly-report/', monthly_report, name='monthly_report'),
    path('employee/<int:employee_id>/daily/', employee_daily_report, name='employee_daily_report'),
    path('settings/', settings_view, name='settings'),
    path('shifts/', shifts_view, name='shifts'),
    path('api/employee/<int:employee_id>/update-hours/', update_employee_hours, name='update_employee_hours'),
    path('api/shift/<int:shift_id>/delete/', delete_shift, name='delete_shift'),
    path('api/employee/<int:employee_id>/assign-shift/', assign_shift, name='assign_shift'),
    
    # Attendance log management
    path('attendance-logs/', manage_attendance_logs, name='manage_attendance_logs'),
    path('api/attendance-log/add/', add_attendance_log, name='add_attendance_log'),
    path('api/attendance-log/<int:log_id>/edit/', edit_attendance_log, name='edit_attendance_log'),
    path('api/attendance-log/<int:log_id>/delete/', delete_attendance_log, name='delete_attendance_log'),
    path('api/attendance-logs/bulk-delete/', bulk_delete_logs, name='bulk_delete_logs'),
]
