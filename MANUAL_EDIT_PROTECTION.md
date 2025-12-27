# Manual Edit Protection for Attendance Logs

## Overview

Attendance logs can now be manually edited through the Django Admin interface, and these edits are **automatically protected from being overridden** during device sync operations.

## Features

### ✅ Automatic Edit Tracking

When you edit an attendance log through the admin interface:
- ✅ **Automatically marked** as manually edited
- ✅ **Timestamp recorded** when the edit was made
- ✅ **User tracked** who made the edit
- ✅ **Protected from sync** - device sync will NOT override these logs

### ✅ Sync Protection

During device sync operations:
- ✅ Manually edited logs are **preserved**
- ✅ Sync only adds new logs or updates non-edited ones
- ✅ Log messages show how many edited logs were protected
- ✅ No data loss from manual corrections

## How It Works

### Database Fields

Three new fields added to `AttendanceLog` model:

| Field | Type | Description |
|-------|------|-------------|
| `is_manually_edited` | Boolean | True if log was manually edited |
| `edited_at` | DateTime | When the log was last edited |
| `edited_by` | String | Username of who edited it |

### Automatic Protection

**When you edit a log in admin:**
1. Open Django Admin → Attendance logs
2. Click on any log to edit it
3. Make your changes
4. Click "Save"
5. **Automatically:**
   - `is_manually_edited` = True
   - `edited_at` = Current timestamp
   - `edited_by` = Your username

**During sync:**
1. Device sync fetches new attendance data
2. System checks existing logs
3. Logs with `is_manually_edited=True` are **skipped**
4. Only non-edited logs can be updated
5. New logs are added normally

## Using the Feature

### Editing Attendance Logs

**Via Django Admin:**

1. **Access Admin Panel**
   ```
   http://your-server:8000/admin/
   ```

2. **Navigate to Attendance Logs**
   - Click **"Attendance logs"** under **ATTENDANCE**

3. **Find the Log to Edit**
   - Use filters: Status, Manually Edited, Date
   - Use search: Employee name or ID
   - Click on the log

4. **Make Your Changes**
   - Edit employee, timestamp, status, or verification mode
   - Optionally check "Is manually edited" (auto-checked on save)

5. **Save**
   - Click **"Save"**
   - Log is now protected from sync

### Viewing Edit Status

**In Admin List View:**
- Column: **"Is manually edited"** - Shows ✓ or ✗
- Column: **"Edited by"** - Shows username
- Column: **"Edited at"** - Shows edit timestamp

**Filter Options:**
- Filter by: **"Is manually edited"** - Yes/No
- Filter by: **"Status"** - Check-in/Check-out
- Filter by: **"Timestamp"** - Date range

### Manually Marking Logs

You can also manually mark logs as edited without changing data:

1. Open the log in admin
2. Check the box: **"Is manually edited"**
3. Save
4. Log is now protected

## Use Cases

### Common Scenarios

**1. Correcting Wrong Timestamps**
```
Employee forgot to check out → Admin edits timestamp → Protected from sync
```

**2. Fixing Status Errors**
```
Device recorded wrong status → Admin corrects it → Sync won't revert it
```

**3. Adding Missing Logs**
```
Device missed a punch → Admin adds manually → Won't be duplicated by sync
```

**4. Removing Duplicate Logs**
```
Device created duplicates → Admin deletes/edits → Sync won't recreate them
```

## Technical Details

### Sync Logic

**Before (Old Behavior):**
```python
# Sync would override ALL existing logs
existing_logs = AttendanceLog.objects.filter(timestamp__range=(min_ts, max_ts))
# Could overwrite manual edits!
```

**After (New Behavior):**
```python
# Sync preserves manually edited logs
existing_logs_query = AttendanceLog.objects.filter(timestamp__range=(min_ts, max_ts))
manually_edited = existing_logs_query.filter(is_manually_edited=True)
# Manually edited logs are skipped!
logger.info(f"Found {len(manually_edited)} manually edited logs - preserved")
```

### Admin Integration

**Auto-tracking in save_model:**
```python
def save_model(self, request, obj, form, change):
    if change:  # Only for updates
        obj.is_manually_edited = True
        obj.edited_at = timezone.now()
        obj.edited_by = request.user.username
    super().save_model(request, obj, form, change)
```

## Migration

### Database Changes

Migration: `0008_add_manual_edit_tracking.py`

**Fields Added:**
- `is_manually_edited` - Boolean, default=False
- `edited_at` - DateTime, nullable
- `edited_by` - String(150), nullable

**Backward Compatible:**
- Existing logs: `is_manually_edited=False`
- Can be edited and protected going forward
- No data loss

### Applying Migration

```bash
# Already applied if you're reading this!
python manage.py migrate
```

## Best Practices

### When to Edit Logs

✅ **Good Reasons to Edit:**
- Correcting obvious device errors
- Fixing timestamp mistakes
- Adding missing punches
- Removing duplicates
- Correcting wrong status codes

⚠️ **Be Careful:**
- Editing affects payroll calculations
- Document why you made changes
- Consider adding notes/comments
- Review daily summaries after editing

### Workflow Recommendations

1. **Before Editing:**
   - Verify the error
   - Check with employee if needed
   - Document the reason

2. **After Editing:**
   - Verify daily summary updated correctly
   - Check if overtime calculations affected
   - Notify payroll team if needed

3. **Regular Audits:**
   - Review manually edited logs monthly
   - Check who edited what
   - Ensure edits are justified

## Monitoring

### Checking Protected Logs

**Via Admin:**
```
Filter: Is manually edited = Yes
```

**Via Django Shell:**
```python
from attendance.models import AttendanceLog

# Count manually edited logs
edited_count = AttendanceLog.objects.filter(is_manually_edited=True).count()
print(f"Manually edited logs: {edited_count}")

# See recent edits
recent_edits = AttendanceLog.objects.filter(
    is_manually_edited=True
).order_by('-edited_at')[:10]

for log in recent_edits:
    print(f"{log.employee.name} - {log.timestamp} - Edited by {log.edited_by}")
```

### Sync Logs

Check sync logs to see protection in action:

```bash
# View logs
docker logs spti_consumer -f

# Look for:
"Found X manually edited logs - these will be preserved"
```

## Troubleshooting

### Log Still Being Overridden

**Problem:** Edited log was overridden by sync

**Solutions:**
1. Check `is_manually_edited` is True
2. Verify migration applied: `python manage.py showmigrations`
3. Check sync logs for protection message
4. Ensure you saved the edit in admin

### Can't Edit Logs

**Problem:** Fields are read-only in admin

**Solutions:**
1. Make sure you're logged in as superuser
2. Check admin permissions
3. Verify you're in edit mode, not add mode

### Edit Tracking Not Working

**Problem:** `edited_by` or `edited_at` not populated

**Solutions:**
1. Ensure you're editing through admin (not shell)
2. Check you're logged in (username needed)
3. Verify `save_model` method is working

## Security Considerations

### Access Control

- Only **superusers** can edit attendance logs by default
- Edit tracking provides **audit trail**
- Can't delete edit history (fields are readonly)

### Data Integrity

- Manual edits are **clearly marked**
- **Who** and **when** is always tracked
- Can filter/report on edited logs
- Sync protection prevents accidental overwrites

## Future Enhancements

Potential improvements:

- [ ] Add "reason for edit" field
- [ ] Email notifications on edits
- [ ] Bulk edit protection
- [ ] Edit approval workflow
- [ ] Detailed audit log
- [ ] Revert to original functionality

## Summary

### Key Benefits

✅ **No More Lost Edits** - Manual corrections are preserved  
✅ **Automatic Protection** - No extra steps needed  
✅ **Full Audit Trail** - Track who edited what and when  
✅ **Transparent** - Clear indicators in admin UI  
✅ **Backward Compatible** - Existing logs work normally  

### Quick Reference

| Action | Result |
|--------|--------|
| Edit log in admin | Auto-marked as manually edited |
| Save edited log | Protected from sync |
| Sync runs | Skips manually edited logs |
| View logs | See edit status and details |
| Filter logs | Find all manual edits |

---

**Version**: 2.0  
**Feature Added**: December 26, 2025  
**Status**: ✅ Production Ready  
**Migration**: 0008_add_manual_edit_tracking
