@echo off
REM Script to import attendance history data into Docker PostgreSQL database

echo ========================================
echo SPTI Payroll - Import Historical Data
echo ========================================
echo.
echo This will import October-December 2025 attendance data
echo into the PostgreSQL database used by Docker.
echo.

echo Step 1: Syncing employees from ZK device...
docker-compose exec backend python manage.py sync_employees
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: Could not sync from device. Creating employees manually...
    docker-compose exec backend python create_employees.py
)

echo.
echo Step 2: Importing attendance history from CSV...
docker-compose exec backend python populate_attendance_history.py

echo.
echo Step 3: Calculating daily summaries...
docker-compose exec backend python manage.py calculate_summaries --start-date 2025-10-01 --end-date 2025-12-31

echo.
echo ========================================
echo Import Complete!
echo ========================================
echo.
echo Verifying data...
docker-compose exec backend python -c "from attendance.models import Employee, AttendanceLog, DailySummary; print(f'Employees: {Employee.objects.count()}'); print(f'Attendance Logs: {AttendanceLog.objects.count()}'); print(f'Nov 2025 Summaries: {DailySummary.objects.filter(date__year=2025, date__month=11).count()}')"

echo.
echo ========================================
echo Next Steps:
echo 1. Open your browser
echo 2. Go to http://localhost:8001/monthly-report/?year=2025^&month=11
echo 3. You should see data for November 2025!
echo ========================================
pause
