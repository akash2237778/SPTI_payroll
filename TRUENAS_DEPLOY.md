# 🚀 TrueNAS Deployment Guide - Updated

## Prerequisites
- TrueNAS SCALE with Dockge installed
- Docker images pushed to Docker Hub (tag: 0.1)
- Network access to biometric device (192.168.2.66)

---

## Deployment Options

### Option 1: Standard Bridge Network (Try This First) ⭐

Use this if your TrueNAS and biometric device are on the same network.

**File**: `docker-compose.truenas.yml`

#### Steps:

1. **Open Dockge**: `http://<truenas-ip>:5001`
2. **Create Stack**: Click "+ Compose"
3. **Name**: `spti-payroll`
4. **Copy** contents from `docker-compose.truenas.yml`
5. **Deploy**

#### Verification:

```bash
# SSH to TrueNAS
ssh root@<truenas-ip>

# Check logs
docker logs spti_consumer --tail 50
```

Expected:
```
✅ Successfully connected to Kafka.
✅ Initial startup sync completed successfully.
```

---

### Option 2: Macvlan Network (If Bridge Doesn't Work)

Use this if the consumer can't reach the biometric device with standard bridge network.

**File**: `docker-compose.truenas-macvlan.yml`

#### Before Deploying:

1. **Find your network interface**:
   ```bash
   ip addr show
   ```
   Look for: `enp0s31f6`, `eno1`, `br0`, etc.

2. **Update the compose file**:
   ```yaml
   parent: enp0s31f6           # ← Your interface
   gateway: 192.168.2.55        # ← Your router IP
   ipv4_address: 192.168.2.200  # ← Unused IP on your network
   ```

3. **Deploy** in Dockge

---

## Configuration

### Images Used
```yaml
backend: akash7778/sptipayroll-backend:0.1
consumer: akash7778/sptipayroll-consumer:0.1
```

### Ports
- **8001**: Web interface
- **9092**: Kafka (internal)
- **5432**: PostgreSQL (internal)
- **2181**: Zookeeper (internal)

### Environment Variables
```yaml
POSTGRES_HOST: db
KAFKA_BOOTSTRAP_SERVERS: kafka:9092
DJANGO_DEBUG: "True"
ALLOWED_HOSTS: "*"
```

---

## Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Dashboard** | `http://<truenas-ip>:8001` | Main interface |
| **Admin** | `http://<truenas-ip>:8001/admin/` | Django admin |
| **Sync API** | `http://<truenas-ip>:8001/sync-logs/` | Manual sync |

---

## Verification Checklist

- [ ] All containers running: `docker ps`
- [ ] Consumer connected to Kafka: `docker logs spti_consumer`
- [ ] Backend running: `docker logs spti_backend`
- [ ] Web interface accessible: `http://<truenas-ip>:8001`
- [ ] Sync works: Click "Sync Now" on dashboard

---

## Troubleshooting

### Issue 1: Consumer can't reach device

**Symptoms**:
```
Error: can't reach device (ping 192.168.2.66)
```

**Solution**:
1. Try Option 2 (macvlan network)
2. Verify device IP is correct
3. Check TrueNAS can ping device:
   ```bash
   ping 192.168.2.66
   ```

### Issue 2: "No such file /app/manage.py"

**Cause**: Using volume mounts with pre-built images

**Solution**: Remove volume mounts (already fixed in provided files)

### Issue 3: Database connection refused

**Symptoms**:
```
connection to server at "localhost" refused
```

**Solution**: Ensure `POSTGRES_HOST: db` (not `localhost`)

### Issue 4: Kafka not available

**Wait**: Kafka takes ~30 seconds to start. Check:
```bash
docker logs spti_kafka
```

---

## Post-Deployment

### 1. Create Admin User

```bash
docker exec -it spti_backend python manage.py createsuperuser
```

### 2. Configure Shifts

1. Go to: `http://<truenas-ip>:8001/admin/`
2. Login with admin credentials
3. Add/configure shifts

### 3. Test Sync

1. Go to dashboard
2. Click "Sync Now"
3. Wait ~6 seconds
4. Verify data appears

---

## Updates

### Pull Latest Images

```bash
docker-compose pull
docker-compose up -d --force-recreate
```

### Backup Database

```bash
docker exec spti_db pg_dump -U postgres spti_db > backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
cat backup_20251220.sql | docker exec -i spti_db psql -U postgres spti_db
```

---

## Production Checklist

- [ ] Change `DJANGO_DEBUG` to `"False"`
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Configure `ALLOWED_HOSTS` to specific IPs
- [ ] Set up SSL/HTTPS (reverse proxy)
- [ ] Configure regular backups
- [ ] Test failover scenarios

---

## Files

1. **`docker-compose.truenas.yml`** - Standard deployment (try first)
2. **`docker-compose.truenas-macvlan.yml`** - Advanced networking
3. **`TRUENAS_DEPLOY.md`** - This guide

---

## Quick Deploy

### Using Dockge:

1. Open Dockge
2. Create stack: `spti-payroll`
3. Copy from `docker-compose.truenas.yml`
4. Deploy
5. Access: `http://<truenas-ip>:8001`

### Using SSH:

```bash
# Copy file to TrueNAS
scp docker-compose.truenas.yml root@<truenas-ip>:/mnt/tank/apps/spti-payroll/docker-compose.yml

# Deploy
ssh root@<truenas-ip>
cd /mnt/tank/apps/spti-payroll
docker-compose up -d
```

---

## Support

**Logs**:
```bash
docker logs spti_backend
docker logs spti_consumer
docker logs spti_kafka
```

**Restart Services**:
```bash
docker restart spti_consumer
docker restart spti_backend
```

**Full Restart**:
```bash
docker-compose down
docker-compose up -d
```

---

**Start with `docker-compose.truenas.yml` for easiest deployment!** 🚀
