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
    View to manage attendance logs - list, search, filter.
    Displays Daily Summaries with grouped logs, mimicking the report view.
    """
    import datetime
    
    # Get filter parameters
    employee_id = request.GET.get('employee_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Default to current month if no dates provided
    if not start_date and not end_date:
        today = datetime.date.today()
        start_date = today.replace(day=1).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')

    # Base query for Summaries
    summaries = DailySummary.objects.select_related('employee').order_by('-date', 'employee__name')
    
    # Apply filters
    if employee_id:
        summaries = summaries.filter(employee_id=employee_id)
    
    if start_date:
        try:
            start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            summaries = summaries.filter(date__gte=start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
            summaries = summaries.filter(date__lte=end)
        except ValueError:
            pass
    
    # Limit number of records if no specific filters to avoid overload
    if not employee_id and not start_date:
        summaries = summaries[:50]
        
    # Fetch related logs for these summaries to display "All Punches"
    # We need a map: (employee_id, date) -> [logs]
    
    # Get the date range and employee scope from the filtered summaries
    # (Optimized approach: Fetch logs only for the displayed summaries)
    # Since 'summaries' is a queryset, we can't easily iterate before slicing if we sliced.
    # But usually this view is paginated. For now, let's just fetch logs for the date range.
    
    # If we have a huge range, this might be heavy. Let's rely on the applied filters.
    logs_query = AttendanceLog.objects.select_related('employee').order_by('timestamp')
    if employee_id:
        logs_query = logs_query.filter(employee_id=employee_id)
    if start_date:
        logs_query = logs_query.filter(timestamp__date__gte=start_date)
    if end_date:
        logs_query = logs_query.filter(timestamp__date__lte=end_date)
        
    logs_by_key = {}
    for log in logs_query:
        key = (log.employee.id, log.timestamp.date())
        if key not in logs_by_key:
            logs_by_key[key] = []
        logs_by_key[key].append(log)

    # Attach logs to summaries for template access
    summary_data = []
    for s in summaries:
        key = (s.employee.id, s.date)
        summary_data.append({
            'summary': s,
            'logs': logs_by_key.get(key, [])
        })

    # Get all employees for dropdown
    employees = Employee.objects.all().order_by('name')
    
    context = {
        'summary_data': summary_data,
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
