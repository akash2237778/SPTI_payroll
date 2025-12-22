# Attendance History Import - Complete Guide

## Overview

This guide explains how to import historical attendance data from `attendance_history.csv` (October, November, December 2025) into your database.

## Quick Start

### Step 1: Sync Employees from Device

First, sync employee data from the ZK biometric device to get real names:

```bash
python manage.py sync_employees
```

This will:
- Connect to the ZK device (configured in settings as `ZK_DEVICE_IP`)
- Fetch all users with their real names
- Create/update employees in the database

**Alternative:** If you can't connect to the device, you can use the fallback script:
```bash
python create_employees.py
```
(This creates employees with placeholder names like "Employee 1", "Employee 2", etc.)

### Step 2: Import Attendance History

Once employees are in the database, import the historical attendance data:

```bash
# First, do a dry run to verify
python populate_attendance_history.py --dry-run

# If everything looks good, run the actual import
python populate_attendance_history.py
```

This will import **~2,119 attendance records** from October-December 2025.

### Step 3: Calculate Daily Summaries ⚠️ IMPORTANT

After importing attendance logs, you MUST calculate daily summaries for the data to appear in reports:

```bash
python manage.py calculate_summaries --start-date 2025-10-01 --end-date 2025-12-31
```

This will:
- Process all attendance logs
- Calculate total hours, overtime, night hours
- Generate DailySummary records needed for monthly reports

**Without this step, the monthly report will show "No attendance data found"!**

## Detailed Workflow

### 1. Analyze the CSV (Optional)

To see what employees and data are in the CSV:

```bash
python analyze_attendance_csv.py
```

This shows:
- Unique biometric IDs in the CSV
- Number of records per employee
- Date ranges for each employee
- Django commands to create employees (if needed)

### 2. Sync Employees

**Option A: From ZK Device (Recommended)**

```bash
python manage.py sync_employees
```

You can specify a custom IP:
```bash
python manage.py sync_employees --ip 192.168.1.100
```

**Option B: Manual Creation (Fallback)**

If the device is not accessible:
```bash
python create_employees.py
```

### 3. Verify Employees

Check that employees were created:

```bash
python manage.py shell
```

```python
from attendance.models import Employee
print(f"Total employees: {Employee.objects.count()}")
for emp in Employee.objects.all():
    print(f"  {emp.biometric_id}: {emp.name}")
```

### 4. Import Attendance Data

**Dry Run (Test Mode):**
```bash
python populate_attendance_history.py --dry-run
```

This will show you:
- How many records will be imported
- Any employees that are missing
- Duplicate detection results
- No data is actually saved

**Actual Import:**
```bash
python populate_attendance_history.py
```

Expected output:
```
STATISTICS:
  Total rows in CSV:           2895
  Filtered out (not Oct-Dec):  0
  Invalid timestamps:          0
  Employee not found:          0
  Duplicates skipped:          ~150
  Successfully created:        ~2119
  Errors:                      0

Date range: 2025-10-01 to 2025-12-20
```

## Files Created

| File | Purpose |
|------|---------|
| `sync_employees.py` | Django command to sync employees from ZK device |
| `create_employees.py` | Fallback script to create employees with placeholder names |
| `analyze_attendance_csv.py` | Analyze CSV and show statistics |
| `populate_attendance_history.py` | Main script to import attendance data |
| `POPULATE_ATTENDANCE_README.md` | Detailed documentation |

## Data Summary

### Employees
- **Total:** 29 unique employees
- **Biometric IDs:** 1, 2, 4, 6, 7, 8, 9, 10, 11, 12, 15, 17, 18, 19, 20, 21, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 44, 55, 9999

### Attendance Records
- **Total:** ~2,895 records in CSV
- **Date Range:** October 1, 2025 - December 20, 2025
- **After Filtering:** ~2,119 unique records (duplicates removed)

### Data Quality
- ✅ All timestamps are valid
- ✅ All employee IDs exist in the device
- ✅ Duplicates are automatically detected and skipped
- ✅ Status field is not used (always set to 0)

## Troubleshooting

### "Employee with biometric_id X not found"

**Solution:** Run `python manage.py sync_employees` first to sync employees from the device.

### "Cannot connect to device"

**Solution:** 
1. Check device IP in settings (`ZK_DEVICE_IP`)
2. Verify network connectivity
3. Use fallback: `python create_employees.py`

### "Duplicates skipped"

This is normal! The CSV contains some duplicate entries. The script automatically:
- Detects duplicates within the CSV
- Checks for existing records in the database
- Skips duplicates to avoid errors

### No records imported

Check:
1. Employees exist in database: `Employee.objects.count()`
2. CSV file is in the correct location
3. Date range matches (Oct-Dec 2025)

## Next Steps

After successful import:

1. **Verify the data:**
   ```python
   from attendance.models import AttendanceLog
   print(f"October: {AttendanceLog.objects.filter(timestamp__month=10).count()}")
   print(f"November: {AttendanceLog.objects.filter(timestamp__month=11).count()}")
   print(f"December: {AttendanceLog.objects.filter(timestamp__month=12).count()}")
   ```

2. **Generate daily summaries** (if needed):
   ```bash
   python manage.py calculate_summaries --start-date 2025-10-01 --end-date 2025-12-20
   ```

3. **Backup the database:**
   ```bash
   python manage.py dumpdata > backup_$(date +%Y%m%d).json
   ```

## Important Notes

- ⚠️ The script filters data to **October-December 2025 only**
- ⚠️ Status field is **not used** in this application (always 0)
- ⚠️ Employee names should be synced from the device for accuracy
- ⚠️ Run migrations before importing: `python manage.py migrate`
- ⚠️ Duplicates are automatically handled and skipped

## Support

If you encounter issues:
1. Run with `--dry-run` to diagnose
2. Check the error messages
3. Verify employee data exists
4. Check CSV file format
5. Review the statistics output
