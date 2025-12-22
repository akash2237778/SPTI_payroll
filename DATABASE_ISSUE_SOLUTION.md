# Database Configuration Issue - FOUND THE PROBLEM!

## 🔴 THE ISSUE

You have **TWO SEPARATE DATABASES**:

### 1. Local Scripts (SQLite) ✅ HAS DATA
- **Database**: `db.sqlite3` (local file)
- **Used by**: 
  - `populate_attendance_history.py`
  - `calculate_summaries`
  - `create_employees.py`
  - Any `python manage.py` commands run locally
- **Status**: Contains all your imported data (166 summaries, 8 employees)

### 2. Docker Web Server (PostgreSQL) ❌ EMPTY
- **Database**: PostgreSQL container `spti_db`
- **Used by**: 
  - Web UI (running on port 8001)
  - Docker backend container
  - Docker consumer container
- **Status**: EMPTY - no data imported yet!

## 🎯 WHY THIS HAPPENED

The `settings.py` checks the `DB_ENGINE` environment variable:
- **No `DB_ENGINE` set** → Uses SQLite (local scripts)
- **`DB_ENGINE=django.db.backends.postgresql`** → Uses PostgreSQL (Docker)

Docker-compose.yml sets `DB_ENGINE: django.db.backends.postgresql` (line 54), so Docker uses PostgreSQL.

## ✅ SOLUTION

Import the data into the **PostgreSQL database** that Docker uses.

### Quick Fix: Run Import Scripts in Docker

```bash
# Step 1: Sync employees from device (or create them)
docker-compose exec backend python manage.py sync_employees

# Alternative if device not available:
docker-compose exec backend python create_employees.py

# Step 2: Import attendance history
docker-compose exec backend python populate_attendance_history.py

# Step 3: Calculate summaries
docker-compose exec backend python manage.py calculate_summaries --start-date 2025-10-01 --end-date 2025-12-31
```

### Verify Data in PostgreSQL

```bash
# Check data in Docker's PostgreSQL
docker-compose exec backend python manage.py shell
```

Then:
```python
from attendance.models import Employee, AttendanceLog, DailySummary
print(f"Employees: {Employee.objects.count()}")
print(f"Attendance Logs: {AttendanceLog.objects.count()}")
print(f"Nov 2025 Summaries: {DailySummary.objects.filter(date__year=2025, date__month=11).count()}")
```

Should show:
- Employees: 29-36
- Attendance Logs: ~800
- Nov 2025 Summaries: 166

### Alternative: Use SQLite in Docker (For Testing)

If you want Docker to use the same SQLite database:

1. **Edit `docker-compose.yml`** - Comment out line 54:
```yaml
environment:
  # DB_ENGINE: django.db.backends.postgresql  # COMMENTED OUT
  POSTGRES_DB: spti_db
```

2. **Restart Docker:**
```bash
docker-compose down
docker-compose up -d
```

3. **The SQLite file is already mounted** via the volume binding, so Docker will use your existing `db.sqlite3` with all the data!

## 🔍 How to Check Which Database You're Using

### Local:
```bash
python check_db_config.py
```
Output: `Engine: django.db.backends.sqlite3`

### Docker:
```bash
docker-compose exec backend python check_db_config.py
```
Output: `Engine: django.db.backends.postgresql`

## 📊 Current State

| Environment | Database | Has Data? |
|-------------|----------|-----------|
| Local scripts | SQLite (`db.sqlite3`) | ✅ YES (166 summaries) |
| Docker web UI | PostgreSQL (`spti_db`) | ❌ NO (empty) |

## 🚀 Recommended Approach

**Use PostgreSQL for production, so import data there:**

```bash
# All in one go:
docker-compose exec backend bash -c "
  python manage.py sync_employees &&
  python populate_attendance_history.py &&
  python manage.py calculate_summaries --start-date 2025-10-01 --end-date 2025-12-31
"
```

Then refresh your browser and the data will appear! 🎉

## 💡 Future Tip

Always run import scripts with the same database as your web server:
- **If using Docker** → Run scripts with `docker-compose exec backend python ...`
- **If running locally** → Make sure `DB_ENGINE` matches in both environments
