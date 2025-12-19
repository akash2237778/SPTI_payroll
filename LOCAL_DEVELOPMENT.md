# 🖥️ Local Development Setup

## Running Consumer Locally on Windows

When developing locally, you can run the consumer on your Windows machine (which can access the biometric device) while other services run in Docker.

---

## Quick Start

### 1. Start Infrastructure (Docker)

```bash
# Use the local development compose file
docker-compose -f docker-compose.local.yml up -d

# Or update your existing docker-compose.yml:
# Change: KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
# To:     KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
```

This starts:
- ✅ PostgreSQL (port 5432)
- ✅ Kafka (port 9092)
- ✅ Zookeeper (port 2181)
- ✅ Backend (port 9000)

### 2. Run Consumer Locally

Double-click: **`run_consumer_local.bat`**

Or manually:
```bash
set POSTGRES_HOST=localhost
set KAFKA_BOOTSTRAP_SERVERS=localhost:9092
python manage.py run_kafka_consumer
```

---

## Why Run Consumer Locally?

| Component | Location | Reason |
|-----------|----------|--------|
| **Consumer** | Windows Host | ✅ Can access biometric device (192.168.2.66) |
| **Backend** | Docker | ✅ Isolated, consistent environment |
| **Database** | Docker | ✅ Easy to reset/manage |
| **Kafka** | Docker | ✅ Message broker infrastructure |

---

## Configuration

### Docker Services (docker-compose.local.yml)

```yaml
kafka:
  environment:
    KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092  # ← Key change
  ports:
    - "9092:9092"

db:
  ports:
    - "5432:5432"  # ← Exposed for local access
```

### Local Consumer Environment

```bash
POSTGRES_HOST=localhost          # ← Not 'db'
POSTGRES_PORT=5432
KAFKA_BOOTSTRAP_SERVERS=localhost:9092  # ← Not 'kafka:9092'
```

---

## Verification

### 1. Check Docker Services

```bash
docker ps
```

Expected:
```
spti_backend     Up
spti_kafka       Up (healthy)
spti_db          Up (healthy)
spti_zookeeper   Up
```

### 2. Test Database Connection

```bash
# From Windows
psql -h localhost -U postgres -d spti_db
# Password: password
```

### 3. Test Kafka Connection

```bash
# List topics
docker exec spti_kafka kafka-topics --bootstrap-server localhost:9092 --list
```

### 4. Run Consumer

```bash
run_consumer_local.bat
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

---

## Troubleshooting

### Issue 1: "NoBrokersAvailable"

**Cause**: Kafka not accessible on localhost:9092

**Fix**:
1. Check Kafka is running: `docker ps | grep kafka`
2. Verify port mapping: `docker port spti_kafka`
3. Check Kafka logs: `docker logs spti_kafka`
4. Restart Kafka:
   ```bash
   docker restart spti_kafka
   ```

### Issue 2: "Connection refused" (Database)

**Cause**: PostgreSQL not exposed

**Fix**:
```yaml
# In docker-compose.yml
db:
  ports:
    - "5432:5432"  # Add this
```

### Issue 3: Consumer can't reach device

**Cause**: Windows firewall or network

**Fix**:
1. Test from Windows: `ping 192.168.2.66`
2. Test port: `telnet 192.168.2.66 4370`
3. Run test script: `python test_zk_connection.py`

### Issue 4: "Module not found"

**Cause**: Missing Python dependencies

**Fix**:
```bash
pip install -r requirements.txt
```

---

## Development Workflow

### 1. Start Infrastructure

```bash
docker-compose -f docker-compose.local.yml up -d
```

### 2. Run Consumer

```bash
run_consumer_local.bat
```

### 3. Access Web Interface

Open: `http://localhost:9000`

### 4. Test Sync

1. Click "Sync Now" on dashboard
2. Watch consumer logs
3. Verify data appears

### 5. Stop Services

```bash
# Stop consumer: Ctrl+C in terminal
# Stop Docker: docker-compose -f docker-compose.local.yml down
```

---

## Production vs Development

| Setting | Development (Local) | Production (TrueNAS) |
|---------|---------------------|----------------------|
| Consumer | Windows host | Docker (macvlan) |
| Database Host | `localhost` | `db` |
| Kafka Host | `localhost:9092` | `kafka:9092` |
| Device Access | Direct | Via macvlan network |
| Kafka Advertised | `localhost:9092` | `kafka:9092` |

---

## Files

1. **`docker-compose.local.yml`** - Local development compose
2. **`run_consumer_local.bat`** - Run consumer on Windows
3. **`docker-compose.truenas-macvlan.yml`** - Production (TrueNAS)

---

## Quick Commands

```bash
# Start infrastructure
docker-compose -f docker-compose.local.yml up -d

# Run consumer locally
run_consumer_local.bat

# View logs
docker logs -f spti_backend
docker logs -f spti_kafka

# Stop everything
docker-compose -f docker-compose.local.yml down

# Restart Kafka (if needed)
docker restart spti_kafka
```

---

## Next Steps

1. ✅ Start Docker services: `docker-compose -f docker-compose.local.yml up -d`
2. ✅ Run consumer: `run_consumer_local.bat`
3. ✅ Test sync from web interface
4. ✅ Develop and test locally
5. ✅ Build images when ready: `build_and_push.bat`
6. ✅ Deploy to TrueNAS: Use `docker-compose.truenas-macvlan.yml`

---

**For local development, use `docker-compose.local.yml` + `run_consumer_local.bat`** 🚀
