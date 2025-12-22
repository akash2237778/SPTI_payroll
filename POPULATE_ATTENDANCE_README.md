# Populate Attendance History Script

## Overview

This script (`populate_attendance_history.py`) is designed to import historical attendance data from `attendance_history.csv` into the database. It specifically handles attendance logs from **October, November, and December 2025**.

## Features

✅ **Date Filtering**: Only imports data from October-December 2025  
✅ **Duplicate Detection**: Skips duplicate entries (both in CSV and database)  
✅ **Employee Mapping**: Maps biometric IDs to employees automatically  
✅ **Bulk Insert**: Uses Django's bulk_create for optimal performance  
✅ **Error Handling**: Gracefully handles missing employees and invalid data  
✅ **Dry Run Mode**: Test the import without modifying the database  
✅ **Detailed Statistics**: Shows comprehensive import statistics  

## Prerequisites

1. Ensure all employees are created in the database with correct `biometric_id` values
2. The CSV file should be in the project root directory
3. Django environment must be properly configured

## Usage

### Basic Usage

```bash
python populate_attendance_history.py
```

This will:
- Read from `attendance_history.csv` in the current directory
- Filter data for October-December 2025
- Import all valid attendance logs to the database

### Dry Run (Testing)

To test the import without saving to the database:

```bash
python populate_attendance_history.py --dry-run
```

This is useful to:
- Check for errors before actual import
- See statistics about what will be imported
- Verify employee mappings

### Custom CSV File

To use a different CSV file:

```bash
python populate_attendance_history.py --csv /path/to/your/file.csv
```

### Help

```bash
python populate_attendance_history.py --help
```

## CSV Format

The script expects a CSV file with the following columns:

| Column    | Description                          | Example              |
|-----------|--------------------------------------|----------------------|
| UserID    | Biometric ID of the employee         | 55                   |
| Timestamp | Date and time of attendance          | 2025-10-01 08:38:52  |
| Punch     | Punch type (not used)                | 0                    |
| Status    | Status text (not used)               | IN                   |

Example CSV:
```csv
UserID,Timestamp,Punch,Status
55,2025-10-01 08:38:52,0,IN
19,2025-10-01 08:42:11,0,IN
28,2025-10-01 08:58:49,0,IN
```

## Output

The script provides detailed statistics:

```
STATISTICS:
  Total rows in CSV:           2897
  Filtered out (not Oct-Nov):  150
  Invalid timestamps:          0
  Employee not found:          5
  Duplicates skipped:          120
  Successfully created:        2622
  Errors:                      0

Date range: 2025-10-01 to 2025-11-30
```

## What Gets Imported

- ✅ All attendance logs from October 2025
- ✅ All attendance logs from November 2025
- ✅ All attendance logs from December 2025
- ❌ Logs from other months (filtered out)
- ❌ Duplicate entries (skipped)
- ❌ Logs for non-existent employees (skipped with warning)

## Troubleshooting

### "Employee with biometric_id X not found"

**Solution**: Create the employee in the database first with the correct biometric_id:
```python
from attendance.models import Employee
Employee.objects.create(
    name="Employee Name",
    employee_id="EMP001",
    biometric_id=X
)
```

### "File not found"

**Solution**: Ensure `attendance_history.csv` is in the project root directory, or use the `--csv` flag to specify the correct path.

### Duplicate Entries

The script automatically handles duplicates. If you see "Duplicates skipped" in the statistics, it means:
- The same attendance log appears multiple times in the CSV, OR
- The log already exists in the database

This is normal and the script will skip these automatically.

## Database Models

The script populates the `AttendanceLog` model:

```python
class AttendanceLog(models.Model):
    employee = ForeignKey(Employee)
    timestamp = DateTimeField()
    status = IntegerField()  # 0 for check-in
    verification_mode = IntegerField()  # Default: 1
```

## Performance

- Uses bulk_create with batch_size=500 for optimal performance
- Processes ~3000 records in under 10 seconds
- Transaction-based to ensure data integrity

## Safety Features

1. **Transaction Rollback**: If any error occurs during bulk insert, all changes are rolled back
2. **Duplicate Protection**: Uses `ignore_conflicts=True` to prevent duplicate key errors
3. **Validation**: Validates all data before attempting to save
4. **Dry Run**: Test mode available to verify before actual import

## Next Steps After Import

After successfully importing the data, you may want to:

1. **Regenerate Daily Summaries**: Run the summary calculation for October-December
2. **Verify Data**: Check the admin panel or run queries to verify the import
3. **Backup Database**: Create a backup after successful import

## Example Workflow

```bash
# 1. First, do a dry run to check everything
python populate_attendance_history.py --dry-run

# 2. Review the statistics and warnings

# 3. If everything looks good, run the actual import
python populate_attendance_history.py

# 4. Verify the import
python manage.py shell
>>> from attendance.models import AttendanceLog
>>> AttendanceLog.objects.filter(timestamp__month=10).count()
>>> AttendanceLog.objects.filter(timestamp__month=11).count()
```

## Support

If you encounter any issues:
1. Check the error messages in the output
2. Run with `--dry-run` to diagnose issues
3. Verify employee biometric IDs match the CSV
4. Check the CSV file format
