# ✅ FINAL DEPLOYMENT CHECKLIST - TrueNAS

## Test Results

✅ **Device Connection Works!**
- Protocol: **TCP** (`force_udp=False`)
- Ping: **Disabled** (`ommit_ping=True`)
- Timeout: **60 seconds**
- Device Firmware: Ver 6.60 May 14 2018
- Users: 36
- Attendance Records: 23

---

## Deployment Steps

### Step 1: Build Docker Images

```bash
cd "C:\Users\Akash\Desktop\SPTI Payroll"

# Build backend
docker build -t akash7778/sptipayroll-backend:latest .

# Build consumer (same image, different command)
docker build -t akash7778/sptipayroll-consumer:latest .
```

### Step 2: Push to Docker Hub

```bash
docker push akash7778/sptipayroll-backend:latest
docker push akash7778/sptipayroll-consumer:latest
```

### Step 3: Deploy on TrueNAS

#### Option A: Using Dockge

1. Open Dockge: `http://<truenas-ip>:5001`
2. Create new stack: `spti-payroll`
3. Copy `docker-compose.truenas-macvlan.yml`
4. **Verify these settings**:
   ```yaml
   parent: enp0s31f6        # ✅ Your interface
   gateway: 192.168.2.55    # ✅ Your gateway
   ipv4_address: 192.168.2.200  # ✅ Unused IP
   ```
5. Click **Deploy**

#### Option B: Using SSH

```bash
# Copy compose file to TrueNAS
scp docker-compose.truenas-macvlan.yml root@<truenas-ip>:/mnt/tank/apps/spti-payroll/docker-compose.yml

# SSH to TrueNAS
ssh root@<truenas-ip>

# Deploy
cd /mnt/tank/apps/spti-payroll
docker-compose pull
docker-compose up -d
```

---

## Verification

### 1. Check Container Status

```bash
docker ps
```

Expected:
```
spti_backend    Up
spti_consumer   Up
spti_kafka      Up (healthy)
spti_db         Up (healthy)
spti_zookeeper  Up
```

### 2. Check Consumer Network

```bash
docker exec spti_consumer ip addr show
```

Should show: `192.168.2.200`

### 3. Test Device Connection from Container

```bash
# Copy test script to TrueNAS
scp test_zk_connection.py root@<truenas-ip>:/tmp/

# Run from consumer
docker cp /tmp/test_zk_connection.py spti_consumer:/tmp/
docker exec spti_consumer python /tmp/test_zk_connection.py
```

Expected:
```
✅ SUCCESS with Config 1: TCP, no ping
Firmware: Ver 6.60 May 14 2018
Users: 36
Attendance records: 23
```

### 4. Check Consumer Logs

```bash
docker logs spti_consumer --tail 50
```

Expected:
```
Initializing Kafka Consumer...
Successfully connected to Kafka.
Listening on topic: attendance_events
Attempting initial sync with 192.168.2.66...
Connecting to device at 192.168.2.66... (Attempt 1/3)
Disabling device for sync...
Fetching users...
Found 36 users
Fetching attendance logs...
Downloaded 23 attendance records
✓ Sync completed successfully
```

### 5. Access Web Interface

Open: `http://<truenas-ip>:8001`

---

## Troubleshooting

### If Consumer Can't Reach Device

1. **Verify macvlan IP**:
   ```bash
   docker exec spti_consumer ip addr show
   ```

2. **Test ping from container**:
   ```bash
   docker exec spti_consumer ping -c 2 192.168.2.66
   ```

3. **Check network interface**:
   ```bash
   # On TrueNAS
   ip link show enp0s31f6
   ```

4. **Verify no IP conflict**:
   ```bash
   # From another machine
   ping 192.168.2.200
   ```
   Should NOT respond before container starts.

### If Macvlan Doesn't Work

**Alternative**: Use host network (may work on TrueNAS)

```yaml
consumer:
  network_mode: "host"
  environment:
    POSTGRES_HOST: localhost
    KAFKA_BOOTSTRAP_SERVERS: localhost:9092
```

---

## Configuration Summary

### Working ZK Parameters
```python
ZK(
    ip='192.168.2.66',
    port=4370,
    timeout=60,
    password=0,
    force_udp=False,    # ✅ TCP works!
    ommit_ping=True     # ✅ Skip ping
)
```

### Network Configuration
```yaml
networks:
  macvlan_network:
    driver: macvlan
    driver_opts:
      parent: enp0s31f6           # Your TrueNAS interface
    ipam:
      config:
        - subnet: 192.168.2.0/24
          gateway: 192.168.2.55    # Your gateway
          ip_range: 192.168.2.200/32

consumer:
  networks:
    spti_network:
    macvlan_network:
      ipv4_address: 192.168.2.200  # Consumer's LAN IP
```

---

## Post-Deployment

### Create Admin User

```bash
docker exec -it spti_backend python manage.py createsuperuser
```

### Test Sync

1. Go to: `http://<truenas-ip>:8001`
2. Click **"Sync Now"**
3. Wait ~6 seconds
4. Check dashboard for updated data

### Configure Shifts

1. Go to: `http://<truenas-ip>:8001/admin/`
2. Login with admin credentials
3. Configure shifts, employees, settings

---

## Success Criteria

- ✅ All containers running
- ✅ Consumer has macvlan IP (192.168.2.200)
- ✅ Consumer can reach device (192.168.2.66)
- ✅ Sync completes successfully
- ✅ Web interface accessible
- ✅ Data appears on dashboard

---

## Files to Deploy

1. **Docker Images** (on Docker Hub):
   - `akash7778/sptipayroll-backend:latest`
   - `akash7778/sptipayroll-consumer:latest`

2. **Compose File**:
   - `docker-compose.truenas-macvlan.yml`

3. **Test Script** (optional):
   - `test_zk_connection.py`

---

## Ready to Deploy! 🚀

The code is confirmed working. The only remaining step is ensuring the macvlan network on TrueNAS allows the consumer to reach the device.

**Next**: Build images → Push to Docker Hub → Deploy on TrueNAS
