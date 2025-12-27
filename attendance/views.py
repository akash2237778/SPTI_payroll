from django.shortcuts import render
from django.db.models import Count
from django.utils import timezone
from .models import Employee, AttendanceLog, DailySummary
import json
from django.http import JsonResponse
from django.conf import settings
from kafka import KafkaProducer
import logging

logger = logging.getLogger(__name__)

def index(request):
    try:
        today = timezone.localdate()
    except Exception:
        # Fallback if timezone not configured locally or other issue
        import datetime
        today = datetime.date.today()
    
    # Stats
    total_employees = Employee.objects.count()
    logs_today_count = AttendanceLog.objects.filter(timestamp__date=today).count()
    last_log = AttendanceLog.objects.order_by('-timestamp').first()
    last_sync_time = last_log.timestamp if last_log else None
    
    # Data
    daily_summaries = list(DailySummary.objects.filter(date=today).select_related('employee'))
    recent_logs = AttendanceLog.objects.select_related('employee').order_by('-timestamp')[:50]
    
    # Attach all punches for today to summaries
    today_logs = AttendanceLog.objects.filter(timestamp__date=today).order_by('timestamp')
    punches_map = {}
    for log in today_logs:
        if log.employee_id not in punches_map:
            punches_map[log.employee_id] = []
        punches_map[log.employee_id].append(log.timestamp)
        
    for summary in daily_summaries:
        summary.punches = punches_map.get(summary.employee.id, [])

    context = {
        'total_employees': total_employees,
        'logs_today_count': logs_today_count,
        'last_sync_time': last_sync_time,
        'daily_summaries': daily_summaries,
        'recent_logs': recent_logs
    }
    return render(request, 'index.html', context)

def trigger_sync_view(request):

    """
    Producer: Pushes a sync task to Kafka.
    """
    from .models import DeviceSettings
    device_settings = DeviceSettings.get_settings()
    device_ip = request.GET.get('ip', device_settings.device_ip)
    
    try:
        producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        message = {
            "action": "sync_attendance", 
            "device_ip": device_ip
        }
        
        producer.send(settings.KAFKA_ATTENDANCE_TOPIC, message)
        producer.flush()
        producer.close()
        
        return JsonResponse({'status': 'success', 'data': message})
    except Exception as e:
        logger.error(f"Kafka Error: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def monthly_report(request):
    import datetime
    
    try:
        today = datetime.date.today()
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except (ValueError, TypeError):
        today = datetime.date.today()
        year = today.year
        month = today.month

    # Fetch summaries for the month
    summaries = DailySummary.objects.filter(
        date__year=year, 
        date__month=month
    ).select_related('employee').order_by('employee__name', 'date')
    
    # Process data in Python
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

    # Calculate Prev/Next
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    context = {
        'report_data': report_data,
        'year': year,
        'month': month,
        'month_name': datetime.date(year, month, 1).strftime('%B'),
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year
    }
    return render(request, 'monthly_report.html', context)

def employee_daily_report(request, employee_id):
    """
    Shows daily attendance details for a specific employee for a given month
    """
    import datetime
    
    try:
        employee = Employee.objects.get(id=employee_id)
    except Employee.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Employee not found'}, status=404)
    
    try:
        today = datetime.date.today()
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except (ValueError, TypeError):
        today = datetime.date.today()
        year = today.year
        month = today.month
    
    # Fetch daily summaries for this employee for the month
    daily_summaries = DailySummary.objects.filter(
        employee=employee,
        date__year=year,
        date__month=month
    ).order_by('date')
    
    # Fetch all logs for this employee for the month for detailed view
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    start_date = datetime.date(year, month, 1)
    end_date = datetime.date(year, month, last_day)
    
    # Group logs by date
    logs_by_date = {}
    all_logs = AttendanceLog.objects.filter(
        employee=employee,
        timestamp__date__gte=start_date,
        timestamp__date__lte=end_date
    ).order_by('timestamp')
    
    for log in all_logs:
        date_key = log.timestamp.date()
        if date_key not in logs_by_date:
            logs_by_date[date_key] = []
        logs_by_date[date_key].append(log)
    
    # Combine summaries with detailed logs
    daily_data = []
    for summary in daily_summaries:
        daily_data.append({
            'date': summary.date,
            'first_check_in': summary.first_check_in,
            'last_check_out': summary.last_check_out,
            'total_hours': summary.total_hours,
            'is_overtime': summary.is_overtime,
            'overtime_hours': summary.overtime_hours,
            'logs': logs_by_date.get(summary.date, [])
        })
    
    # Calculate Prev/Next
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year
    
    # Calculate totals
    total_days = daily_summaries.count()
    total_hours = sum(float(s.total_hours) for s in daily_summaries)
    
    # Use employee's working hours for overtime calculation
    expected_hours = employee.working_hours if employee.working_hours else 8.0
    overtime_hours = sum(float(s.overtime_hours) for s in daily_summaries)
    
    avg_hours = round(total_hours / total_days, 2) if total_days > 0 else 0.0
    
    context = {
        'employee': employee,
        'daily_data': daily_data,
        'year': year,
        'month': month,
        'month_name': datetime.date(year, month, 1).strftime('%B'),
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'total_days': total_days,
        'total_hours': round(total_hours, 2),
        'overtime_hours': round(overtime_hours, 2),
        'avg_hours': avg_hours
    }
    return render(request, 'employee_daily_report.html', context)

def settings_view(request):
    """
    View and update work settings
    """
    from .models import WorkSettings
    
    settings = WorkSettings.get_settings()
    
    if request.method == 'POST':
        try:
            # Update settings from form
            settings.default_working_hours = float(request.POST.get('default_working_hours', 8.0))
            settings.lunch_start_time = request.POST.get('lunch_start_time', '13:00:00')
            settings.lunch_end_time = request.POST.get('lunch_end_time', '13:30:00')
            settings.exclude_lunch_from_hours = request.POST.get('exclude_lunch_from_hours') == 'on'
            settings.save()
            
            return JsonResponse({'status': 'success', 'message': 'Settings updated successfully'})
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    # GET request - show settings page
    employees = Employee.objects.all().order_by('name')
    
    context = {
        'settings': settings,
        'employees': employees
    }
    return render(request, 'settings.html', context)

def update_employee_hours(request, employee_id):
    """
    Update working hours for a specific employee
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)
    
    try:
        employee = Employee.objects.get(id=employee_id)
        working_hours = request.POST.get('working_hours')
        
        if working_hours:
            employee.working_hours = float(working_hours)
        else:
            employee.working_hours = None  # Use default
        
        employee.save()
        
        return JsonResponse({
            'status': 'success', 
            'message': f'Updated working hours for {employee.name}',
            'working_hours': employee.get_working_hours()
        })
    except Employee.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Employee not found'}, status=404)
    except Exception as e:
        logger.error(f"Error updating employee hours: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def shifts_view(request):
    """
    View and manage shifts
    """
    from .models import Shift
    
    if request.method == 'POST':
        try:
            # Create or update shift
            shift_id = request.POST.get('shift_id')
            
            if shift_id:
                # Update existing shift
                shift = Shift.objects.get(id=shift_id)
            else:
                # Create new shift
                shift = Shift()
            
            shift.name = request.POST.get('name')
            shift.shift_type = request.POST.get('shift_type', 'DAY')
            shift.start_time = request.POST.get('start_time')
            shift.end_time = request.POST.get('end_time')
            shift.working_hours = float(request.POST.get('working_hours', 8.0))
            
            # Break times (optional)
            break_start = request.POST.get('break_start_time')
            break_end = request.POST.get('break_end_time')
            shift.break_start_time = break_start if break_start else None
            shift.break_end_time = break_end if break_end else None
            shift.exclude_break = request.POST.get('exclude_break') == 'on'
            
            shift.night_shift_allowance = float(request.POST.get('night_shift_allowance', 0.0))
            shift.is_active = request.POST.get('is_active') == 'on'
            
            shift.save()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Shift "{shift.name}" saved successfully'
            })
        except Exception as e:
            logger.error(f"Error saving shift: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    # GET request - show shifts page
    shifts = Shift.objects.all().order_by('name')
    employees = Employee.objects.all().select_related('shift').order_by('name')
    
    context = {
        'shifts': shifts,
        'employees': employees
    }
    return render(request, 'shifts.html', context)


def delete_shift(request, shift_id):
    """
    Delete a shift
    """
    from .models import Shift
    
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)
    
    try:
        shift = Shift.objects.get(id=shift_id)
        shift_name = shift.name
        shift.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Shift "{shift_name}" deleted successfully'
        })
    except Shift.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Shift not found'}, status=404)
    except Exception as e:
        logger.error(f"Error deleting shift: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def assign_shift(request, employee_id):
    """
    Assign a shift to an employee
    """
    from .models import Shift
    
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)
    
    try:
        employee = Employee.objects.get(id=employee_id)
        shift_id = request.POST.get('shift_id')
        
        if shift_id:
            shift = Shift.objects.get(id=shift_id)
            employee.shift = shift
        else:
            employee.shift = None  # Unassign shift
        
        employee.save()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Shift assigned to {employee.name}',
            'shift_name': employee.shift.name if employee.shift else 'None'
        })
    except Employee.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Employee not found'}, status=404)
    except Shift.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Shift not found'}, status=404)
    except Exception as e:
        logger.error(f"Error assigning shift: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

