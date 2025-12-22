"""
Additional views for attendance log management (CRUD operations)
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Employee, AttendanceLog, DailySummary
from .services import BiometricService
import logging

logger = logging.getLogger(__name__)


def manage_attendance_logs(request):
    """
    View to manage attendance logs - list, search, filter
    """
    import datetime
    
    # Get filter parameters
    employee_id = request.GET.get('employee_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Base query
    logs = AttendanceLog.objects.select_related('employee').order_by('-timestamp')
    
    # Apply filters
    if employee_id:
        logs = logs.filter(employee_id=employee_id)
    
    if start_date:
        try:
            start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            logs = logs.filter(timestamp__date__gte=start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
            logs = logs.filter(timestamp__date__lte=end)
        except ValueError:
            pass
    
    # Limit to recent 100 logs for performance
    logs = logs[:100]
    
    # Get all employees for dropdown
    employees = Employee.objects.all().order_by('name')
    
    context = {
        'logs': logs,
        'employees': employees,
        'selected_employee_id': int(employee_id) if employee_id else None,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'manage_attendance_logs.html', context)


@require_http_methods(["POST"])
def add_attendance_log(request):
    """
    Add a new attendance log manually
    """
    try:
        employee_id = request.POST.get('employee_id')
        timestamp_str = request.POST.get('timestamp')
        
        # Validate employee
        employee = get_object_or_404(Employee, id=employee_id)
        
        # Parse timestamp
        try:
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M')
            # Make timezone aware if needed
            if timezone.is_aware(timezone.now()):
                timestamp = timezone.make_aware(timestamp, timezone.get_current_timezone())
        except ValueError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid timestamp format'
            }, status=400)
        
        # Check for duplicate
        if AttendanceLog.objects.filter(employee=employee, timestamp=timestamp).exists():
            return JsonResponse({
                'status': 'error',
                'message': 'An attendance log already exists for this employee at this time'
            }, status=400)
        
        # Create log
        log = AttendanceLog.objects.create(
            employee=employee,
            timestamp=timestamp,
            status=0,
            verification_mode=1
        )
        
        # Recalculate summaries for affected date
        service = BiometricService()
        affected_keys = {(employee.id, timestamp.date())}
        service._update_summaries(affected_keys)
        
        return JsonResponse({
            'status': 'success',
            'message': f'Attendance log added for {employee.name}',
            'log': {
                'id': log.id,
                'employee_name': employee.name,
                'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except Exception as e:
        logger.error(f"Error adding attendance log: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@require_http_methods(["POST"])
def edit_attendance_log(request, log_id):
    """
    Edit an existing attendance log
    """
    try:
        log = get_object_or_404(AttendanceLog, id=log_id)
        old_date = log.timestamp.date()
        old_employee_id = log.employee.id
        
        timestamp_str = request.POST.get('timestamp')
        
        # Parse new timestamp
        try:
            new_timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M')
            if timezone.is_aware(timezone.now()):
                new_timestamp = timezone.make_aware(new_timestamp, timezone.get_current_timezone())
        except ValueError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid timestamp format'
            }, status=400)
        
        # Check for duplicate (excluding current log)
        if AttendanceLog.objects.filter(
            employee=log.employee,
            timestamp=new_timestamp
        ).exclude(id=log_id).exists():
            return JsonResponse({
                'status': 'error',
                'message': 'An attendance log already exists for this employee at this time'
            }, status=400)
        
        # Update log
        log.timestamp = new_timestamp
        log.save()
        
        # Recalculate summaries for affected dates
        service = BiometricService()
        affected_keys = {
            (old_employee_id, old_date),
            (log.employee.id, new_timestamp.date())
        }
        service._update_summaries(affected_keys)
        
        return JsonResponse({
            'status': 'success',
            'message': f'Attendance log updated for {log.employee.name}',
            'log': {
                'id': log.id,
                'employee_name': log.employee.name,
                'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except Exception as e:
        logger.error(f"Error editing attendance log: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@require_http_methods(["POST"])
def delete_attendance_log(request, log_id):
    """
    Delete an attendance log
    """
    try:
        log = get_object_or_404(AttendanceLog, id=log_id)
        employee_id = log.employee.id
        log_date = log.timestamp.date()
        employee_name = log.employee.name
        
        # Delete the log
        log.delete()
        
        # Recalculate summaries for affected date
        service = BiometricService()
        affected_keys = {(employee_id, log_date)}
        service._update_summaries(affected_keys)
        
        return JsonResponse({
            'status': 'success',
            'message': f'Attendance log deleted for {employee_name}'
        })
        
    except Exception as e:
        logger.error(f"Error deleting attendance log: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@require_http_methods(["POST"])
def bulk_delete_logs(request):
    """
    Delete multiple attendance logs at once
    """
    try:
        log_ids = request.POST.getlist('log_ids[]')
        
        if not log_ids:
            return JsonResponse({
                'status': 'error',
                'message': 'No logs selected'
            }, status=400)
        
        # Get affected dates before deletion
        logs = AttendanceLog.objects.filter(id__in=log_ids)
        affected_keys = {(log.employee.id, log.timestamp.date()) for log in logs}
        
        # Delete logs
        count, _ = logs.delete()
        
        # Recalculate summaries
        if affected_keys:
            service = BiometricService()
            service._update_summaries(affected_keys)
        
        return JsonResponse({
            'status': 'success',
            'message': f'Deleted {count} attendance log(s)'
        })
        
    except Exception as e:
        logger.error(f"Error bulk deleting logs: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
