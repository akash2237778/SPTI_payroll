# TrueNAS SCALE Deployment Guide - SPTI Payroll

Complete guide for deploying SPTI Payroll on TrueNAS SCALE using Dockge or Docker Compose.

---

## 📋 Prerequisites

1. **TrueNAS SCALE** installed (Electric Eel 24.10+ recommended)
2. **Dockge** installed (or Docker Compose CLI)
3. **Network access** to biometric device (192.168.2.66)
4. **SSH access** to TrueNAS (optional, for troubleshooting)

---

## 🚀 Deployment Methods

### Method 1: Using Dockge (Recommended)

#### Step 1: Create New Stack in Dockge

1. Open Dockge web interface: `http://<truenas-ip>:5001`
2. Click **"+ Compose"**
3. Name your stack: `spti-payroll`
4. Copy the contents of `docker-compose.truenas.yml` into the editor

#### Step 2: Configure Environment

The compose file uses these images:
- `akash7778/sptipayroll-backend:latest`
- `akash7778/sptipayroll-consumer:latest`

**Important**: These images have the code built-in. Do NOT add volume mounts for `/app`.

#### Step 3: Deploy

1. Click **"Deploy"** in Dockge
2. Wait for all containers to start (green status)
3. Check logs for any errors

---

### Method 2: Using Docker Compose CLI

#### Step 1: Create Directory

```bash
mkdir -p /mnt/tank/apps/spti-payroll
cd /mnt/tank/apps/spti-payroll
```

#### Step 2: Create docker-compose.yml

Copy the contents of `docker-compose.truenas.yml` to `/mnt/tank/apps/spti-payroll/docker-compose.yml`

#### Step 3: Deploy

```bash
docker-compose up -d
```

---

## 📝 Docker Compose Configuration

### Key Points

1. **No Volume Mounts for Code**
   ```yaml
   # ❌ WRONG - Don't do this with pre-built images
   volumes:
     - ./:/app
   
   # ✅ CORRECT - No volume mount needed
   image: akash7778/sptipayroll-backend:latest
   ```

2. **Named Volume for Database**
   ```yaml
   volumes:
     - postgres_data:/var/lib/postgresql/data
   
   volumes:
     postgres_data:  # Named volume (managed by Docker)
   ```

3. **Consumer Network Mode**
   ```yaml
   network_mode: "host"  # Allows access to LAN devices
   ```
   
   **Note**: Consumer uses `host` network to access the biometric device at `192.168.2.66`

---

## 🔧 Configuration

### Environment Variables

All configuration is done via environment variables in the compose file:

```yaml
environment:
  POSTGRES_HOST: localhost  # For consumer (host network)
  POSTGRES_HOST: db         # For backend (bridge network)
  KAFKA_BOOTSTRAP_SERVERS: localhost:9092  # For consumer
  KAFKA_BOOTSTRAP_SERVERS: kafka:9092      # For backend
  DJANGO_DEBUG: "True"
  ALLOWED_HOSTS: "*"
```

### Biometric Device IP

The device IP is configured in Django settings:
- Default: `192.168.2.66`
- Port: `4370`

To change, rebuild the image with updated `settings.py`.

---

## 🌐 Access Points

After deployment:

| Service | URL | Description |
|---------|-----|-------------|
| **Dashboard** | `http://<truenas-ip>:8001` | Main web interface |
| **Sync API** | `http://<truenas-ip>:8001/sync-logs/` | Trigger manual sync |
| **Monthly Report** | `http://<truenas-ip>:8001/monthly-report/` | View reports |
| **Shift Management** | `http://<truenas-ip>:8001/shifts/` | Manage shifts |
| **Admin Panel** | `http://<truenas-ip>:8001/admin/` | Django admin |

**Default Admin Credentials**: Create via Django shell (see below)

---

## ✅ Verification

### Check Container Status

```bash
docker ps
```

Expected output:
```
CONTAINER ID   IMAGE                                    STATUS
xxxxx          akash7778/sptipayroll-backend:latest    Up (healthy)
xxxxx          akash7778/sptipayroll-consumer:latest   Up
xxxxx          confluentinc/cp-kafka:7.5.0             Up (healthy)
xxxxx          confluentinc/cp-zookeeper:7.5.0         Up
xxxxx          postgres:15                             Up (healthy)
```

### Check Consumer Logs

```bash
docker logs spti_consumer --tail 50
```

Expected output:
```
Initializing Kafka Consumer...
Successfully connected to Kafka.
Listening on topic: attendance_events
Attempting initial sync with 192.168.2.66...
Connecting to device at 192.168.2.66... (Attempt 1/3)
✓ Sync completed successfully
```

### Check Backend Logs

```bash
docker logs spti_backend --tail 50
```

Expected output:
```
Operations to perform:
  Apply all migrations: admin, attendance, auth, contenttypes, sessions
Running migrations:
  No migrations to apply.
[INFO] Listening at: http://0.0.0.0:8000
```

---

## 🔐 Create Admin User

```bash
docker exec -it spti_backend python manage.py createsuperuser
```

Follow prompts to create username and password.

---

## 🐛 Troubleshooting

### Issue 1: "No such file or directory: /app/manage.py"

**Cause**: Volume mount conflicts with pre-built image

**Solution**: Remove volume mounts from backend and consumer services
```yaml
# Remove this:
volumes:
  - type: bind
    source: .
    target: /app
```

### Issue 2: Consumer can't reach biometric device

**Cause**: Network isolation

**Solution**: Ensure `network_mode: "host"` is set for consumer
```yaml
consumer:
  network_mode: "host"
  environment:
    POSTGRES_HOST: localhost  # Important!
    KAFKA_BOOTSTRAP_SERVERS: localhost:9092  # Important!
```

### Issue 3: Database connection refused

**Cause**: Consumer using wrong host due to network mode

**Solution**: Consumer must use `localhost`, backend uses `db`
```yaml
# Consumer (host network)
POSTGRES_HOST: localhost

# Backend (bridge network)
POSTGRES_HOST: db
```

### Issue 4: Kafka connection issues

**Check Kafka health**:
```bash
docker exec spti_kafka kafka-topics --bootstrap-server localhost:9092 --list
```

**Restart Kafka**:
```bash
docker restart spti_kafka
docker restart spti_consumer
```

### Issue 5: Permission denied on postgres_data

```bash
# On TrueNAS
chown -R 999:999 /var/lib/docker/volumes/spti-payroll_postgres_data/_data
```

---

## 🔄 Updates

### Update Images

```bash
# Pull latest images
docker pull akash7778/sptipayroll-backend:latest
docker pull akash7778/sptipayroll-consumer:latest

# Recreate containers
docker-compose up -d --force-recreate
```

### Backup Database

```bash
docker exec spti_db pg_dump -U postgres spti_db > backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
cat backup_20251219.sql | docker exec -i spti_db psql -U postgres spti_db
```

---

## 📊 Monitoring

### View All Logs

```bash
docker-compose logs -f
```

### View Specific Service

```bash
docker logs -f spti_backend
docker logs -f spti_consumer
docker logs -f spti_kafka
```

### Check Resource Usage

```bash
docker stats
```

---

## 🎯 Production Checklist

- [ ] Change `DJANGO_DEBUG` to `"False"`
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Configure `ALLOWED_HOSTS` to specific IPs
- [ ] Set up SSL/HTTPS (use reverse proxy)
- [ ] Configure regular database backups
- [ ] Set up monitoring/alerting
- [ ] Test biometric device connectivity
- [ ] Create admin user
- [ ] Configure shifts in admin panel
- [ ] Test sync functionality

---

## 📞 Support

For issues or questions:
1. Check container logs
2. Verify network connectivity to biometric device
3. Ensure all containers are healthy
4. Review this guide's troubleshooting section

---

## 🎉 Success!

Once deployed, you should see:
- ✅ All containers running and healthy
- ✅ Web interface accessible at port 8001
- ✅ Consumer successfully syncing with biometric device
- ✅ Database persisting data

Your SPTI Payroll system is now live on TrueNAS SCALE! 🚀
