# SPTI Payroll - Complete Documentation

**Attendance Management System with ZK Biometric Device Integration**

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Admin Credentials](#admin-credentials)
3. [Device Settings Configuration](#device-settings-configuration)
4. [Deployment Guide](#deployment-guide)
5. [Troubleshooting](#troubleshooting)
6. [Management Commands](#management-commands)
7. [System Architecture](#system-architecture)

---

## Quick Start

### Local Development

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Migrations**
   ```bash
   python manage.py migrate
   ```

3. **Create Admin User**
   ```bash
   python manage.py createsuperuser
   ```
   - Username: `admin`
   - Password: (choose a password)
   - Email: (optional)

4. **Start Server**
   ```bash
   python manage.py runserver
   ```

5. **Access Admin**
   - URL: `http://localhost:8000/admin/`
   - Login with credentials from step 3

6. **Configure Device IP**
   - Go to **Device Settings** in admin
   - Update the device IP address
   - Click **Save**

### Docker Deployment

1. **Start Services**
   ```bash
   docker-compose up -d
   ```

2. **Run Migrations**
   ```bash
   docker exec -it spti_backend python manage.py migrate
   ```

3. **Create Admin User**
   ```bash
   docker exec -it spti_backend python manage.py createsuperuser
   ```

4. **Access Admin**
   - URL: `http://your-server-ip:8000/admin/`

---

## Admin Credentials

### Creating Admin User

**Interactive Method (Recommended):**
```bash
python manage.py createsuperuser
```

**Quick Method (Development Only):**
```bash
python manage.py shell
```
```python
from django.contrib.auth.models import User
User.objects.create_superuser('admin', 'admin@localhost', 'admin123')
exit()
```

**⚠️ Security Notes:**
- Development: Simple passwords like `admin123` are OK
- Production: Use strong passwords (8+ chars, mixed case, numbers, symbols)
- Never use default credentials in production

### Resetting Password

```bash
python manage.py changepassword <username>
```

---

## Device Settings Configuration

### ⭐ NEW FEATURE: Configure Device IP from UI

**No restart required! No environment variables! No container rebuild!**

### How to Configure

1. **Access Django Admin**
   - Go to: `http://your-server:8000/admin/`
   - Login with admin credentials

2. **Navigate to Device Settings**
   - Look for **"ATTENDANCE"** section
   - Click **"Device Settings"**

3. **Update Settings**
   - Click on the existing settings entry
   - Update **Device IP** (e.g., `192.168.2.66`)
   - Optionally update:
     - **Device Port** (default: `4370`)
     - **Timeout** (default: `60` seconds)
   - Click **"Save"**

4. **Test Connection**
   - Go to dashboard
   - Click **"Trigger Sync"**
   - Verify connection works

### Configurable Parameters

| Setting | Default | Description |
|---------|---------|-------------|
| Device IP | 192.168.2.66 | IP address of ZK biometric device |
| Device Port | 4370 | Connection port |
| Timeout | 60 | Connection timeout (seconds) |
| Password | 0 | Device password |
| Force UDP | ✓ | Use UDP protocol |
| Omit Ping | ✓ | Skip ping check |

### Benefits

✅ Change IP instantly without restart  
✅ No need to modify environment variables  
✅ No container rebuild required  
✅ User-friendly web interface  
✅ Changes take effect immediately  

---

## Deployment Guide

### Prerequisites

- Python 3.8+
- PostgreSQL (production) or SQLite (development)
- Kafka + Zookeeper
- ZK Biometric Device on same network

### Environment Variables

Create `.env` file:

```bash
# Django Settings
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False
ALLOWED_HOSTS=*

# Database (PostgreSQL)
DB_ENGINE=django.db.backends.postgresql
POSTGRES_DB=spti_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# Device (Initial value only - configure via admin UI after deployment)
ZK_DEVICE_IP=192.168.2.66
```

### Docker Compose Deployment

**docker-compose.yml** is already configured. Just run:

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f consumer

# Stop services
docker-compose down
```

### Post-Deployment Steps

1. **Verify Services Running**
   ```bash
   docker-compose ps
   ```
   All services should show "Up"

2. **Run Migrations**
   ```bash
   docker exec -it spti_backend python manage.py migrate
   ```

3. **Create Admin User**
   ```bash
   docker exec -it spti_backend python manage.py createsuperuser
   ```

4. **Configure Device Settings**
   - Access admin UI
   - Update device IP if needed

5. **Test Sync**
   - Trigger manual sync from UI
   - Check consumer logs for success

### TrueNAS SCALE Deployment

1. **Network Configuration**
   - Ensure TrueNAS can reach device IP
   - Use macvlan network if needed
   - Configure static IP for consumer

2. **Deploy via Dockge**
   - Import docker-compose.yml
   - Set environment variables
   - Start stack

3. **Verify Network**
   ```bash
   docker exec spti_consumer ping <device-ip>
   ```

---

## Troubleshooting

### Cannot Connect to Device

**Symptoms:**
- "Connection timeout" errors
- "Cannot reach device" messages
- Sync fails

**Solutions:**

1. **Verify Device IP**
   - Check Device Settings in admin
   - Ping device: `ping <device-ip>`
   - Ensure device is powered on

2. **Check Network**
   ```bash
   # From host
   ping 192.168.2.66
   
   # From container
   docker exec spti_consumer ping 192.168.2.66
   ```

3. **Verify Port**
   ```bash
   telnet 192.168.2.66 4370
   # or
   nc -zv 192.168.2.66 4370
   ```

4. **Increase Timeout**
   - Go to Device Settings
   - Increase timeout to 120 seconds
   - Save and retry

5. **Check Firewall**
   - Ensure port 4370 is open
   - Check device firewall settings

### No Data in UI

**Symptoms:**
- Dashboard shows no employees
- No attendance logs
- Empty reports

**Solutions:**

1. **Trigger Manual Sync**
   - Go to dashboard
   - Click "Trigger Sync"
   - Wait for completion

2. **Check Device Connection**
   - Verify device IP is correct
   - Test connection (see above)

3. **Run Debug Sync**
   ```bash
   python manage.py debug_sync
   ```

4. **Check Logs**
   ```bash
   # Backend logs
   docker logs spti_backend
   
   # Consumer logs
   docker logs spti_consumer
   ```

5. **Verify Kafka**
   ```bash
   docker logs kafka
   docker logs zookeeper
   ```

### Summaries Not Generated

**Symptoms:**
- Attendance logs exist but no daily summaries
- Reports show zero hours

**Solutions:**

1. **Recalculate Summaries**
   ```bash
   python manage.py calculate_summaries
   ```

2. **Reprocess Date Range**
   ```bash
   python manage.py reprocess_summaries --start-date 2025-01-01 --end-date 2025-01-31
   ```

3. **Check Shift Assignments**
   - Ensure employees have shifts assigned
   - Verify shift times are correct

4. **Check Work Settings**
   - Go to Work Settings in admin
   - Verify working hours configured

### Docker Issues

**Container Won't Start:**
```bash
# Check logs
docker-compose logs backend

# Rebuild
docker-compose build --no-cache backend
docker-compose up -d
```

**Database Connection Failed:**
```bash
# Check database is running
docker-compose ps db

# Check environment variables
docker exec spti_backend env | grep POSTGRES
```

**Kafka Not Ready:**
```bash
# Wait for Kafka to be ready (takes 30-60 seconds)
docker-compose logs kafka

# Restart consumer after Kafka is ready
docker-compose restart consumer
```

### Admin UI Issues

**Cannot Access Admin:**
- Verify server is running: `docker-compose ps`
- Check URL: `http://localhost:8000/admin/`
- Clear browser cache
- Try incognito/private mode

**Device Settings Not Visible:**
- Verify migrations ran: `python manage.py showmigrations`
- Check you're logged in as superuser
- Restart Django server

**Cannot Save Settings:**
- Check IP format (xxx.xxx.xxx.xxx)
- Ensure port is a number
- Verify timeout is positive

---

## Management Commands

### Sync Commands

**Debug Sync** (with detailed output):
```bash
python manage.py debug_sync
```

**Sync Employees** (from device):
```bash
python manage.py sync_employees
```

**Run Kafka Consumer** (background service):
```bash
python manage.py run_kafka_consumer
```

### Summary Commands

**Calculate Daily Summaries**:
```bash
python manage.py calculate_summaries
```

**Reprocess Summaries** (for date range):
```bash
python manage.py reprocess_summaries --start-date 2025-01-01 --end-date 2025-01-31
```

### Database Commands

**Run Migrations**:
```bash
python manage.py migrate
```

**Create Migrations**:
```bash
python manage.py makemigrations
```

**Database Shell**:
```bash
python manage.py dbshell
```

**Django Shell**:
```bash
python manage.py shell
```

### Utility Commands

**Create Superuser**:
```bash
python manage.py createsuperuser
```

**Change Password**:
```bash
python manage.py changepassword <username>
```

**Collect Static Files**:
```bash
python manage.py collectstatic
```

---

## System Architecture

### Components

1. **Django Backend**
   - REST API endpoints
   - Admin interface
   - Business logic
   - Database models

2. **Kafka Consumer**
   - Background service
   - Listens for sync events
   - Processes attendance data
   - Updates database

3. **PostgreSQL Database**
   - Stores all data
   - Employees, attendance logs, summaries
   - Configuration (shifts, settings)

4. **Kafka + Zookeeper**
   - Message broker
   - Event streaming
   - Decouples sync operations

### Data Flow

```
ZK Device → BiometricService → Kafka → Consumer → Database → Admin UI/Reports
                                  ↑
                                  |
                            Trigger Sync (UI)
```

### Models

**Employee**
- Personal information
- Biometric ID mapping
- Shift assignment
- Custom working hours

**AttendanceLog**
- Raw attendance records
- Timestamp, status
- Linked to employee

**DailySummary**
- Aggregated daily data
- First check-in, last check-out
- Total hours, overtime, night hours

**Shift**
- Shift configuration
- Start/end times
- Break times
- Night shift allowance

**WorkSettings**
- Global work configuration
- Default working hours
- Lunch break times

**DeviceSettings** ⭐
- Device connection settings
- IP, port, timeout
- Configurable from UI

### Ports

| Service | Port | Description |
|---------|------|-------------|
| Backend | 8000 | Django web server |
| PostgreSQL | 5432 | Database |
| Kafka | 9092 | Message broker |
| Zookeeper | 2181 | Kafka coordination |
| Device | 4370 | ZK biometric device |

---

## Features

### Core Features

✅ **Biometric Integration** - Seamless ZK device sync  
✅ **Real-time Sync** - Kafka-based event streaming  
✅ **Shift Management** - Day/night/flexible shifts  
✅ **Overtime Tracking** - Automatic calculation  
✅ **Night Allowance** - Configurable percentages  
✅ **Daily Summaries** - Automated generation  
✅ **Monthly Reports** - Comprehensive reports  

### NEW: Configurable Device Settings

✅ **UI Configuration** - Change IP from admin  
✅ **No Restart** - Immediate effect  
✅ **No Rebuild** - No container changes  
✅ **User Friendly** - Simple web interface  
✅ **Centralized** - All settings in one place  

---

## API Endpoints

### Trigger Sync
```
GET /trigger-sync/
GET /trigger-sync/?ip=192.168.2.100
```

### Monthly Report
```
GET /monthly-report/
GET /monthly-report/?month=12&year=2025
```

### Employee Daily Report
```
GET /employee/<employee_id>/daily-report/
GET /employee/<employee_id>/daily-report/?month=12&year=2025
```

---

## Best Practices

### Security

- Use strong admin passwords in production
- Keep `DJANGO_SECRET_KEY` secret
- Set `DJANGO_DEBUG=False` in production
- Use HTTPS in production
- Limit superuser accounts

### Maintenance

- Regular database backups
- Monitor disk space
- Check logs regularly
- Update dependencies periodically
- Test sync operations daily

### Performance

- Use PostgreSQL in production (not SQLite)
- Configure proper database indexes
- Monitor Kafka disk usage
- Optimize query performance
- Use caching where appropriate

---

## Support

### Documentation
- This file contains all essential information
- Check troubleshooting section first
- Review error messages carefully

### Logs
```bash
# Backend logs
docker logs spti_backend -f

# Consumer logs
docker logs spti_consumer -f

# All logs
docker-compose logs -f
```

### Testing
```bash
# Test device settings
python test_device_settings.py

# Run Django tests
python manage.py test
```

---

## Changelog

### Version 2.0 (Current)
- ✨ NEW: Configurable device settings from UI
- ✨ Device IP, port, timeout now in database
- ✨ No restart required for settings changes
- 🔧 Updated all sync operations
- 📝 Comprehensive documentation

### Version 1.0
- Initial release
- ZK device integration
- Kafka-based sync
- Shift management
- Overtime tracking

---

**Last Updated**: December 26, 2025  
**Version**: 2.0  
**Status**: Production Ready
