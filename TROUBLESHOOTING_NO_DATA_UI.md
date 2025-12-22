# Troubleshooting: No Data Showing in Monthly Report UI

## ✅ Data Verification - PASSED

The data IS in the database:
- ✅ 166 daily summaries for November 2025
- ✅ 8 employees with attendance data
- ✅ View logic returns data correctly
- ✅ Database: SQLite at `C:\Users\Akash\Desktop\SPTI Payroll\db.sqlite3`

## 🔍 Root Cause

The data exists but the UI isn't showing it. This means:

**The web server needs to be restarted!**

When you calculated the summaries, the web server was already running with the old data cached in memory or using an old database connection.

## 🚀 Solution

### Step 1: Stop the Web Server

If running locally with `runserver`:
```bash
# Press Ctrl+C in the terminal where the server is running
```

If running with Docker:
```bash
docker-compose down
# or
docker-compose restart backend
```

### Step 2: Restart the Web Server

**Local Development:**
```bash
python manage.py runserver
```

**Docker:**
```bash
docker-compose up -d
# or
docker-compose restart backend
```

### Step 3: Clear Browser Cache

1. Open the monthly report page
2. Press **Ctrl + Shift + R** (Windows) or **Cmd + Shift + R** (Mac) to hard refresh
3. Or open in incognito/private mode

### Step 4: Verify

Navigate to: `http://localhost:8000/monthly-report/?year=2025&month=11`

You should see data for 8 employees:
- Ajay: 22 days, 238.98 hours
- Amarnath: 15 days, 164.12 hours
- Arvind: 23 days, 394.58 hours
- Essl: 27 days, 314.81 hours
- Pappu: 7 days, 448.17 hours
- Ramdev: 28 days, 346.93 hours
- Shubash: 21 days, 209.84 hours
- Simon: 23 days, 247.29 hours

## 🔧 Additional Checks

### Check if server is running:
```bash
# Windows
netstat -ano | findstr :8000

# Look for LISTENING on port 8000
```

### Test the view directly:
```bash
python debug_monthly_report.py
```

This should show the 8 employees with data.

### Check database file:
```bash
python check_db_config.py
```

Should show:
- Engine: django.db.backends.sqlite3
- Size: ~0.28 MB
- Path exists

## 📊 Quick Data Verification

Run this to verify data is still there:
```bash
python manage.py shell
```

Then:
```python
from attendance.models import DailySummary
nov_count = DailySummary.objects.filter(date__year=2025, date__month=11).count()
print(f"November 2025 summaries: {nov_count}")
# Should print: November 2025 summaries: 166
```

## ⚠️ Common Issues

### Issue: "Still no data after restart"

**Check:**
1. Are you looking at the correct month? (November 2025)
2. Is the URL correct? `?year=2025&month=11`
3. Try a different browser
4. Check browser console for JavaScript errors (F12)

### Issue: "Server won't start"

**Check:**
1. Port 8000 already in use?
2. Database locked?
3. Check error messages in terminal

### Issue: "Different data in UI vs database"

**Possible causes:**
1. Multiple database files (check settings)
2. Docker using different volume
3. Environment variables pointing to different DB

## 🎯 Most Likely Solution

**Just restart the web server!**

The calculate_summaries command modified the database, but the running web server still has old data in memory or cached queries.

```bash
# Stop server (Ctrl+C)
# Start server
python manage.py runserver

# Then hard refresh browser (Ctrl+Shift+R)
```

That should fix it! 🎉
